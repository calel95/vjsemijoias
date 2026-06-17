from typing import Any

from fastapi import APIRouter, Body, Depends, HTTPException
from fastapi.responses import JSONResponse
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from backend.auth import admin_claims, optional_claims, required_claims
from backend.database import get_db
from backend.models import Coupon, Newsletter, Order, Product, User
from backend.services.common import get_or_404
from backend.services.orders import (
    configured_shipping,
    create_local_order,
    money,
    normalize_order_status,
    validate_order_data,
)
from backend.store_config import effective_store_settings, public_store_config


router = APIRouter(prefix="/api")


@router.post("/orders", status_code=201)
def create_order(
    data: dict[str, Any] = Body(default_factory=dict),
    claims=Depends(optional_claims),
    db: Session = Depends(get_db),
):
    try:
        totals = validate_order_data(db, data)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    order = create_local_order(
        db, data, totals, data.get("payment_method", "manual"), claims
    )
    db.commit()
    return order.to_dict()


@router.get("/orders")
def get_orders(claims=Depends(required_claims), db: Session = Depends(get_db)):
    statement = select(Order).order_by(Order.created_at.desc())
    if not claims.get("is_admin"):
        statement = statement.where(Order.user_id == int(claims["sub"]))
    return [order.to_dict() for order in db.scalars(statement).all()]


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
    _claims=Depends(admin_claims),
    db: Session = Depends(get_db),
):
    order = get_or_404(db, Order, order_id)
    order.status = normalize_order_status(data.get("status"))
    db.commit()
    return order.to_dict()


@router.post("/newsletter")
def subscribe_newsletter(
    data: dict[str, Any] = Body(default_factory=dict),
    db: Session = Depends(get_db),
):
    active_settings = effective_store_settings(db)
    email = data.get("email", "")
    if not email or "@" not in email:
        raise HTTPException(status_code=400, detail="E-mail invalido")

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
    active_settings = effective_store_settings(db)
    code = data.get("code", "").upper()
    if not active_settings.coupon.enabled:
        raise HTTPException(status_code=404, detail="Cupons desativados")
    coupon = db.scalar(
        select(Coupon).where(Coupon.code == code, Coupon.is_active.is_(True))
    )
    if not coupon:
        raise HTTPException(status_code=404, detail="Cupom invalido ou expirado")
    if coupon.used_count >= coupon.usage_limit:
        raise HTTPException(status_code=400, detail="Cupom esgotado")
    return {
        "valid": True,
        "code": coupon.code,
        "discount_percent": coupon.discount_percent,
        "message": f"Cupom {coupon.code} aplicado! {coupon.discount_percent:.0f}% de desconto",
    }


@router.post("/shipping/calculate")
def calculate_shipping(
    data: dict[str, Any] = Body(default_factory=dict),
    db: Session = Depends(get_db),
):
    try:
        shipping_data = configured_shipping(data.get("total", 0), db)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {
        "shipping": float(shipping_data["shipping"]),
        "message": shipping_data["message"],
        "estimated_days": shipping_data["estimated_days"],
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
        "total_revenue": total_revenue,
        "recent_orders": [order.to_dict() for order in recent_orders],
    }
