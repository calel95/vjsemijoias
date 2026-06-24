from typing import Any

from fastapi import APIRouter, Body, Depends, HTTPException, Request
from fastapi.responses import JSONResponse
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from backend.auth import admin_claims, optional_claims, required_claims
from backend.database import get_db
from backend.models import Coupon, Newsletter, Order, Product, User, utc_now
from backend.services.common import get_or_404
from backend.services.orders import (
    apply_paid_status,
    create_local_order,
    existing_order_by_idempotency_key,
    money,
    normalize_order_status,
    validate_order_data,
)
from backend.services.shipping import (
    build_shipping_package,
    calculate_shipping_options,
    serialize_shipping_option,
)
from backend.services.admin_security import record_admin_audit
from backend.services.coupons import (
    normalize_coupon_payload,
    validate_coupon_for_order,
)
from backend.services.order_events import record_status_event
from backend.services.transactional_emails import (
    send_order_created_email,
    send_order_shipped_email,
)
from backend.services.validation import clean_text, normalize_email
from backend.store_config import effective_store_settings, public_store_config


router = APIRouter(prefix="/api")


def shipping_quote_input(data: dict[str, Any], db: Session):
    raw_items = data.get("items")
    if not raw_items:
        return money(data.get("total", 0)), None
    if not isinstance(raw_items, list):
        raise ValueError("items deve ser uma lista")

    product_ids = []
    quantities = {}
    for item in raw_items:
        try:
            product_id = int(item["id"])
            quantity = int(item.get("quantity", 1))
        except (KeyError, TypeError, ValueError) as exc:
            raise ValueError("Item de frete invalido") from exc
        if quantity < 1 or quantity > 20:
            raise ValueError("A quantidade deve estar entre 1 e 20")
        if product_id not in quantities:
            product_ids.append(product_id)
            quantities[product_id] = 0
        quantities[product_id] += quantity

    if not product_ids:
        raise ValueError("Informe ao menos um item para calcular frete")

    products = db.scalars(
        select(Product).where(
            Product.id.in_(product_ids),
            Product.is_active.is_(True),
            Product.stock_status != "out_of_stock",
        )
    ).all()
    products_by_id = {product.id: product for product in products}
    if len(products_by_id) != len(product_ids):
        raise ValueError("Um ou mais produtos nao estao disponiveis")

    subtotal = money("0")
    shipping_items = []
    for product_id in product_ids:
        product = products_by_id[product_id]
        quantity = quantities[product_id]
        subtotal += money(product.price) * quantity
        shipping_items.append((product, quantity))
    return subtotal, build_shipping_package(shipping_items)


@router.post("/orders", status_code=201)
def create_order(
    data: dict[str, Any] = Body(default_factory=dict),
    claims=Depends(optional_claims),
    db: Session = Depends(get_db),
):
    try:
        existing_order = existing_order_by_idempotency_key(db, data)
        if existing_order:
            return existing_order.to_dict()
        totals = validate_order_data(db, data)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    order = create_local_order(
        db, data, totals, data.get("payment_method", "manual"), claims
    )
    db.commit()
    send_order_created_email(order)
    return order.to_dict()


@router.get("/orders")
def get_orders(claims=Depends(required_claims), db: Session = Depends(get_db)):
    statement = select(Order).order_by(Order.created_at.desc())
    if not claims.get("is_admin"):
        statement = statement.where(Order.user_id == int(claims["sub"]))
    return [order.to_dict() for order in db.scalars(statement).all()]


@router.get("/orders/{order_id}/public")
def get_public_order(
    order_id: str,
    token: str = "",
    db: Session = Depends(get_db),
):
    order = get_or_404(db, Order, order_id)
    if not order.public_token or token != order.public_token:
        raise HTTPException(status_code=404, detail="Pedido nao encontrado")
    data = order.to_dict()
    data["payment"] = order.payment.to_dict(include_pix=False) if order.payment else None
    return data


@router.get("/orders/{order_id}")
def get_order(
    order_id: str,
    claims=Depends(required_claims),
    db: Session = Depends(get_db),
):
    order = get_or_404(db, Order, order_id)
    if not claims.get("is_admin") and order.user_id != int(claims["sub"]):
        raise HTTPException(status_code=403, detail="Acesso negado")
    return order.to_dict()


@router.put("/admin/orders/{order_id}/status")
def update_order_status(
    order_id: str,
    data: dict[str, Any] = Body(default_factory=dict),
    claims=Depends(admin_claims),
    db: Session = Depends(get_db),
):
    order = get_or_404(db, Order, order_id)
    status = normalize_order_status(data.get("status"))
    previous_status = order.status
    actor_user_id = int(claims["sub"]) if claims and claims.get("sub") else None
    tracking_changed = False
    tracking_metadata = {}
    if "tracking_code" in data:
        tracking_code = clean_text(
            data.get("tracking_code"),
            field="tracking_code",
            max_length=100,
        )
        tracking_changed = tracking_code != (order.tracking_code or "")
        order.tracking_code = tracking_code or None
        tracking_metadata["tracking_code"] = order.tracking_code
    if "tracking_carrier" in data:
        tracking_carrier = clean_text(
            data.get("tracking_carrier"),
            field="tracking_carrier",
            max_length=100,
        )
        tracking_changed = tracking_changed or tracking_carrier != (order.tracking_carrier or "")
        order.tracking_carrier = tracking_carrier or None
        tracking_metadata["tracking_carrier"] = order.tracking_carrier
    if status == "shipped" and not order.shipped_at:
        order.shipped_at = utc_now()
    if status == "delivered" and not order.delivered_at:
        order.delivered_at = utc_now()
    should_send_shipped_email = status == "shipped" and (
        previous_status != status or tracking_changed
    )
    if status == "paid":
        try:
            apply_paid_status(db, order, actor_user_id=actor_user_id)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
    else:
        order.status = status
        if previous_status != status or tracking_changed:
            record_status_event(
                db,
                order,
                status,
                actor_user_id=actor_user_id,
                metadata=tracking_metadata,
            )
    db.commit()
    if should_send_shipped_email:
        send_order_shipped_email(order)
    return order.to_dict()


@router.post("/newsletter")
def subscribe_newsletter(
    data: dict[str, Any] = Body(default_factory=dict),
    db: Session = Depends(get_db),
):
    active_settings = effective_store_settings(db)
    try:
        email = normalize_email(data.get("email"))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    coupon_percent = float(money(active_settings.coupon.discount_percent))
    if db.scalar(select(Newsletter).where(Newsletter.email == email)):
        if not active_settings.coupon.enabled or not active_settings.coupon.code:
            return {"message": "E-mail ja cadastrado!"}
        return {
            "message": (
                f"E-mail ja cadastrado! Use o cupom {active_settings.coupon.code} "
                f"para {coupon_percent:.0f}% off"
            ),
            "coupon": active_settings.coupon.code,
        }

    db.add(
        Newsletter(
            email=email,
            coupon=active_settings.coupon.code if active_settings.coupon.enabled else "",
        )
    )
    db.commit()
    if not active_settings.coupon.enabled or not active_settings.coupon.code:
        return JSONResponse(status_code=201, content={"message": "E-mail cadastrado!"})
    return JSONResponse(
        status_code=201,
        content={
            "message": (
                f"E-mail cadastrado! Use o cupom {active_settings.coupon.code} e ganhe "
                f"{coupon_percent:.0f}% off"
            ),
            "coupon": active_settings.coupon.code,
        },
    )


@router.post("/coupons/validate")
def validate_coupon(
    data: dict[str, Any] = Body(default_factory=dict),
    db: Session = Depends(get_db),
):
    try:
        coupon, discount = validate_coupon_for_order(
            db,
            data.get("code", ""),
            data.get("total", 0),
            customer_email=data.get("customer_email", ""),
            customer_cpf=data.get("customer_cpf", ""),
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    discount_percent = (
        float(coupon.discount_value) if coupon.discount_type == "percent" else 0.0
    )
    return {
        "valid": True,
        "code": coupon.code,
        "discount_percent": discount_percent,
        "discount_type": coupon.discount_type,
        "discount_value": float(coupon.discount_value),
        "minimum_subtotal": float(coupon.minimum_subtotal or 0),
        "discount": float(discount),
        "message": f"Cupom {coupon.code} aplicado!",
    }


@router.get("/admin/coupons")
def list_admin_coupons(
    _claims=Depends(admin_claims),
    db: Session = Depends(get_db),
):
    coupons = db.scalars(select(Coupon).order_by(Coupon.created_at.desc(), Coupon.id.desc())).all()
    return [coupon.to_dict(include_redemptions=True) for coupon in coupons]


@router.post("/admin/coupons", status_code=201)
def create_admin_coupon(
    request: Request,
    data: dict[str, Any] = Body(default_factory=dict),
    claims=Depends(admin_claims),
    db: Session = Depends(get_db),
):
    try:
        payload = normalize_coupon_payload(data)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    if db.scalar(select(Coupon).where(Coupon.code == payload["code"])):
        raise HTTPException(status_code=409, detail="Cupom ja cadastrado")

    coupon = Coupon(**payload)
    if coupon.discount_type == "percent":
        coupon.discount_percent = coupon.discount_value
    db.add(coupon)

    actor = db.get(User, int(claims["sub"])) if claims and claims.get("sub") else None
    record_admin_audit(
        db,
        request,
        "coupon.created",
        admin_user=actor,
        resource="coupon",
        resource_id=payload["code"],
        metadata={
            "code": payload["code"],
            "discount_type": payload["discount_type"],
            "usage_limit": payload["usage_limit"],
            "per_customer_limit": payload["per_customer_limit"],
        },
    )
    db.commit()
    db.refresh(coupon)
    return coupon.to_dict(include_redemptions=True)


@router.put("/admin/coupons/{coupon_id}")
def update_admin_coupon(
    coupon_id: int,
    request: Request,
    data: dict[str, Any] = Body(default_factory=dict),
    claims=Depends(admin_claims),
    db: Session = Depends(get_db),
):
    coupon = get_or_404(db, Coupon, coupon_id)
    try:
        payload = normalize_coupon_payload(data, partial=True)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    if "code" in payload and payload["code"] != coupon.code:
        if db.scalar(select(Coupon).where(Coupon.code == payload["code"])):
            raise HTTPException(status_code=409, detail="Cupom ja cadastrado")

    changed_keys = []
    for key, value in payload.items():
        if getattr(coupon, key) != value:
            setattr(coupon, key, value)
            changed_keys.append(key)
    if coupon.discount_type == "percent":
        coupon.discount_percent = coupon.discount_value

    actor = db.get(User, int(claims["sub"])) if claims and claims.get("sub") else None
    record_admin_audit(
        db,
        request,
        "coupon.updated",
        admin_user=actor,
        resource="coupon",
        resource_id=str(coupon.id),
        metadata={"code": coupon.code, "changed_keys": changed_keys},
    )
    db.commit()
    db.refresh(coupon)
    return coupon.to_dict(include_redemptions=True)


@router.post("/shipping/calculate")
def calculate_shipping(
    data: dict[str, Any] = Body(default_factory=dict),
    db: Session = Depends(get_db),
):
    try:
        subtotal, package = shipping_quote_input(data, db)
        shipping_options = calculate_shipping_options(
            subtotal,
            zip_code=data.get("zip_code", ""),
            package=package,
            db=db,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    serialized_options = [serialize_shipping_option(option) for option in shipping_options]
    selected_option = serialized_options[0]
    return {
        "subtotal": float(subtotal),
        "shipping": selected_option["shipping"],
        "message": selected_option["message"],
        "estimated_days": selected_option["estimated_days"],
        "provider": selected_option["provider"],
        "service": selected_option["service"],
        "destination_zip": selected_option["destination_zip"],
        "package": selected_option["package"],
        "selected_option": selected_option,
        "options": serialized_options,
    }


@router.get("/store/config")
def store_config(db: Session = Depends(get_db)):
    return public_store_config(db)


@router.get("/admin/stats")
def get_admin_stats(
    _claims=Depends(admin_claims),
    db: Session = Depends(get_db),
):
    total_revenue = db.scalar(
        select(func.sum(Order.total)).where(Order.status.in_(["paid", "confirmed"]))
    ) or 0
    recent_orders = db.scalars(
        select(Order).order_by(Order.created_at.desc()).limit(5)
    ).all()
    return {
        "total_products": db.scalar(select(func.count(Product.id))),
        "total_orders": db.scalar(select(func.count(Order.id))),
        "total_users": db.scalar(select(func.count(User.id))),
        "total_newsletter": db.scalar(select(func.count(Newsletter.id))),
        "total_revenue": float(total_revenue),
        "recent_orders": [order.to_dict() for order in recent_orders],
    }
