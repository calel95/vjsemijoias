import json
import secrets
from datetime import datetime
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.models import Coupon, Order, Product
from backend.services.validation import (
    clean_text,
    normalize_email,
    normalize_phone,
    validate_cpf,
)
from backend.services.stock import deduct_stock_for_order, ensure_orderable_stock
from backend.store_config import effective_store_settings


ORDER_STATUSES = {
    "pending",
    "paid",
    "processing",
    "shipped",
    "delivered",
    "canceled",
    "failed",
}


def money(value):
    try:
        return Decimal(str(value)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    except (InvalidOperation, TypeError, ValueError) as exc:
        raise ValueError("Valor monetário inválido") from exc


def configured_shipping(subtotal, db: Session | None = None):
    subtotal = money(subtotal)
    active_settings = effective_store_settings(db)
    mode = active_settings.shipping.mode
    fixed_value = money(active_settings.shipping.fixed_value)
    free_minimum = money(active_settings.shipping.free_minimum)

    if mode == "free":
        shipping = Decimal("0.00")
        message = "Frete Gratis!"
    elif mode == "fixed":
        shipping = fixed_value
        message = f"Frete fixo de R$ {shipping:.2f}"
    elif mode == "threshold":
        if subtotal >= free_minimum:
            shipping = Decimal("0.00")
            message = f"Frete gratis acima de R$ {free_minimum:.2f}"
        else:
            shipping = fixed_value
            message = f"Frete fixo de R$ {shipping:.2f}"
    else:
        raise ValueError("SHIPPING_MODE deve ser free, fixed ou threshold")

    return {
        "shipping": shipping,
        "message": message,
        "estimated_days": active_settings.shipping.estimated_days,
    }


def calculate_order(db: Session, items, coupon_code=""):
    if not isinstance(items, list) or not items:
        raise ValueError("O pedido deve conter ao menos um produto")

    product_ids = []
    quantities = {}
    for item in items:
        try:
            product_id = int(item["id"])
            quantity = int(item.get("quantity", 1))
        except (KeyError, TypeError, ValueError) as exc:
            raise ValueError("Item do pedido inválido") from exc
        if quantity < 1 or quantity > 20:
            raise ValueError("A quantidade deve estar entre 1 e 20")
        if product_id not in quantities:
            product_ids.append(product_id)
            quantities[product_id] = 0
        quantities[product_id] += quantity

    products = db.scalars(
        select(Product).where(
            Product.id.in_(product_ids),
            Product.is_active.is_(True),
            Product.stock_status != "out_of_stock",
        )
    ).all()
    products_by_id = {product.id: product for product in products}
    if len(products_by_id) != len(product_ids):
        raise ValueError("Um ou mais produtos não estão disponíveis")

    normalized_items = []
    subtotal = Decimal("0.00")
    for product_id in product_ids:
        product = products_by_id[product_id]
        quantity = quantities[product_id]
        ensure_orderable_stock(product, quantity)
        unit_price = money(product.price)
        subtotal += unit_price * quantity
        normalized_items.append(
            {
                "id": product.id,
                "name": product.name,
                "price": float(unit_price),
                "quantity": quantity,
                "image": product.image,
                "icon": product.icon,
            }
        )

    active_settings = effective_store_settings(db)
    shipping_data = configured_shipping(subtotal, db)
    shipping = shipping_data["shipping"]
    coupon_code = str(coupon_code or "").strip().upper()
    discount = Decimal("0.00")
    if coupon_code:
        if not active_settings.coupon.enabled:
            coupon_code = ""
        else:
            active_coupon_code = active_settings.coupon.code.upper()
            if coupon_code != active_coupon_code:
                raise ValueError("Cupom invalido, expirado ou esgotado")
            coupon = db.scalar(
                select(Coupon).where(
                    Coupon.code == coupon_code,
                    Coupon.is_active.is_(True),
                )
            )
            if not coupon or coupon.used_count >= coupon.usage_limit:
                raise ValueError("Cupom inválido, expirado ou esgotado")
            discount = (subtotal * money(coupon.discount_percent) / Decimal("100")).quantize(
                Decimal("0.01"), rounding=ROUND_HALF_UP
            )

    return {
        "items": normalized_items,
        "subtotal": subtotal,
        "shipping": shipping,
        "discount": discount,
        "total": subtotal + shipping - discount,
        "coupon": coupon_code,
    }


def validate_order_data(db: Session, data):
    for field in ["customer_name", "customer_email", "customer_cpf", "items"]:
        if not data.get(field):
            raise ValueError(f"Campo obrigatório: {field}")
    data["customer_name"] = clean_text(
        data["customer_name"],
        field="customer_name",
        max_length=200,
        required=True,
    )
    data["customer_email"] = normalize_email(data["customer_email"])
    data["customer_cpf"] = validate_cpf(data["customer_cpf"])
    data["customer_phone"] = normalize_phone(data.get("customer_phone"), required=False)
    data["address_zip"] = clean_text(data.get("address_zip"), field="address_zip", max_length=20)
    data["address_street"] = clean_text(
        data.get("address_street"),
        field="address_street",
        max_length=200,
    )
    data["address_number"] = clean_text(
        data.get("address_number"),
        field="address_number",
        max_length=20,
    )
    data["address_complement"] = clean_text(
        data.get("address_complement"),
        field="address_complement",
        max_length=200,
    )
    data["address_neighborhood"] = clean_text(
        data.get("address_neighborhood"),
        field="address_neighborhood",
        max_length=100,
    )
    data["address_city"] = clean_text(data.get("address_city"), field="address_city", max_length=100)
    data["address_state"] = clean_text(data.get("address_state"), field="address_state", max_length=10)
    return calculate_order(db, data["items"], data.get("coupon", ""))


def create_local_order(db: Session, data, totals, payment_method, claims=None):
    order = Order(
        id="VJ" + datetime.now().strftime("%Y%m%d%H%M%S") + secrets.token_hex(2).upper(),
        user_id=int(claims["sub"]) if claims else None,
        customer_name=data["customer_name"],
        customer_email=data["customer_email"],
        customer_cpf=data["customer_cpf"],
        customer_phone=data.get("customer_phone", ""),
        address_zip=data.get("address_zip", ""),
        address_street=data.get("address_street", ""),
        address_number=data.get("address_number", ""),
        address_complement=data.get("address_complement", ""),
        address_neighborhood=data.get("address_neighborhood", ""),
        address_city=data.get("address_city", ""),
        address_state=data.get("address_state", ""),
        items=json.dumps(totals["items"], ensure_ascii=False),
        subtotal=totals["subtotal"],
        shipping=totals["shipping"],
        discount=totals["discount"],
        total=totals["total"],
        payment_method=payment_method,
        status="pending",
        coupon=totals["coupon"],
    )
    db.add(order)
    return order


def normalize_order_status(value):
    status = str(value or "").strip().lower()
    if status not in ORDER_STATUSES:
        raise HTTPException(status_code=400, detail="Status de pedido invalido")
    return status


def apply_paid_status(db: Session, order: Order):
    deduct_stock_for_order(db, order)
    order.status = "paid"
