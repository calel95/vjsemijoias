import json
import secrets
from datetime import datetime
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.models import Order, Product
from backend.services.coupons import redeem_coupon, validate_coupon_for_order
from backend.services.validation import (
    clean_text,
    normalize_email,
    normalize_phone,
    validate_cpf,
)
from backend.services.stock import deduct_stock_for_order, ensure_orderable_stock
from backend.services.order_events import record_status_event
from backend.services.shipping import build_shipping_package, calculate_shipping_options


ORDER_STATUSES = {
    "pending",
    "payment_pending",
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


def configured_shipping(
    subtotal,
    db: Session | None = None,
    *,
    zip_code: str = "",
    package: dict | None = None,
    selected_option_id: str = "",
):
    options = calculate_shipping_options(subtotal, zip_code=zip_code, package=package, db=db)
    selected_option_id = str(selected_option_id or "").strip()
    if selected_option_id:
        for option in options:
            if option["id"] == selected_option_id:
                return option
        raise ValueError("Opcao de frete invalida ou indisponivel")
    return options[0]


def calculate_order(
    db: Session,
    items,
    coupon_code="",
    *,
    customer_email: str = "",
    customer_cpf: str = "",
    zip_code: str = "",
    selected_shipping_option_id: str = "",
):
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
    shipping_items = []
    subtotal = Decimal("0.00")
    for product_id in product_ids:
        product = products_by_id[product_id]
        quantity = quantities[product_id]
        ensure_orderable_stock(product, quantity)
        shipping_items.append((product, quantity))
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

    package = build_shipping_package(shipping_items)
    shipping_data = configured_shipping(
        subtotal,
        db,
        zip_code=zip_code,
        package=package,
        selected_option_id=selected_shipping_option_id,
    )
    shipping = shipping_data["shipping"]
    coupon_code = str(coupon_code or "").strip().upper()
    discount = Decimal("0.00")
    coupon = None
    coupon_id = None
    if coupon_code:
        coupon, discount = validate_coupon_for_order(
            db,
            coupon_code,
            subtotal,
            customer_email=customer_email,
            customer_cpf=customer_cpf,
        )
        coupon_code = coupon.code
        coupon_id = coupon.id
    return {
        "items": normalized_items,
        "subtotal": subtotal,
        "shipping": shipping,
        "shipping_provider": shipping_data["provider"],
        "shipping_service": shipping_data["service"],
        "shipping_message": shipping_data["message"],
        "shipping_estimated_days": shipping_data["estimated_days"],
        "shipping_destination_zip": shipping_data["destination_zip"],
        "shipping_option_id": shipping_data.get("id"),
        "shipping_company_id": shipping_data.get("company_id"),
        "shipping_company": shipping_data.get("company"),
        "discount": discount,
        "total": subtotal + shipping - discount,
        "coupon": coupon_code,
        "coupon_id": coupon_id,
        "coupon_model": coupon,
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
    data["idempotency_key"] = clean_text(
        data.get("idempotency_key"),
        field="idempotency_key",
        max_length=100,
    )
    return calculate_order(
        db,
        data["items"],
        data.get("coupon", ""),
        customer_email=data["customer_email"],
        customer_cpf=data["customer_cpf"],
        zip_code=data.get("address_zip", ""),
        selected_shipping_option_id=data.get("shipping_option_id", ""),
    )


def existing_order_by_idempotency_key(db: Session, data):
    key = clean_text(data.get("idempotency_key"), field="idempotency_key", max_length=100)
    if not key:
        return None
    return db.scalar(select(Order).where(Order.idempotency_key == key))


def create_local_order(
    db: Session,
    data,
    totals,
    payment_method,
    claims=None,
    *,
    initial_status="pending",
):
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
        shipping_provider=totals.get("shipping_provider"),
        shipping_service=totals.get("shipping_service"),
        shipping_estimated_days=totals.get("shipping_estimated_days"),
        shipping_destination_zip=totals.get("shipping_destination_zip"),
        shipping_option_id=totals.get("shipping_option_id"),
        shipping_company_id=totals.get("shipping_company_id"),
        shipping_company=totals.get("shipping_company"),
        discount=totals["discount"],
        total=totals["total"],
        payment_method=payment_method,
        status=initial_status,
        coupon=totals["coupon"],
        idempotency_key=data.get("idempotency_key") or None,
        public_token=secrets.token_urlsafe(24),
    )
    db.add(order)
    if totals.get("coupon_model") and totals["discount"] > Decimal("0.00"):
        redeem_coupon(
            db,
            coupon=totals["coupon_model"],
            order=order,
            discount_amount=totals["discount"],
            customer_email=data["customer_email"],
            customer_cpf=data["customer_cpf"],
        )
    record_status_event(
        db,
        order,
        initial_status,
        metadata={"payment_method": payment_method},
    )
    return order


def normalize_order_status(value):
    status = str(value or "").strip().lower()
    if status not in ORDER_STATUSES:
        raise HTTPException(status_code=400, detail="Status de pedido invalido")
    return status


def apply_paid_status(db: Session, order: Order, *, actor_user_id: int | None = None):
    was_paid = order.status == "paid"
    deduct_stock_for_order(db, order)
    order.status = "paid"
    if not was_paid:
        record_status_event(db, order, "paid", actor_user_id=actor_user_id)
