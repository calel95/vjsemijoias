from typing import Any

from fastapi import APIRouter, Body, Depends, HTTPException, Request
from fastapi.responses import JSONResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.auth import optional_claims
from backend.config import settings
from backend.database import get_db
from backend.infinitepay_client import InfinitePayError, checkout_token
from backend.models import Payment
from backend.services.orders import create_local_order, validate_order_data
from backend.services.payments import cents, infinitepay, public_url, update_infinitepay_payment
from backend.store_config import effective_store_settings


router = APIRouter(prefix="/api/payments")


@router.get("/config")
def payment_config(db: Session = Depends(get_db)):
    active_settings = effective_store_settings(db)
    return {
        "provider": "infinitepay",
        "enabled": bool(settings.infinitepay_handle),
        "max_installments": 12,
        "store": {
            "name": active_settings.brand.name,
            "public_base_url": settings.public_base_url,
        },
    }


@router.get("/{order_id}/status")
def payment_status(order_id: str, token: str = "", db: Session = Depends(get_db)):
    payment = db.scalar(
        select(Payment).where(
            Payment.order_id == order_id,
            Payment.checkout_token == token,
        )
    )
    if not payment:
        raise HTTPException(status_code=404, detail="Pagamento não encontrado")
    return payment.to_dict()


@router.post("/infinitepay/checkout", status_code=201)
def create_infinitepay_checkout(
    request: Request,
    data: dict[str, Any] = Body(default_factory=dict),
    claims=Depends(optional_claims),
    db: Session = Depends(get_db),
):
    try:
        totals = validate_order_data(db, data)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    order = create_local_order(db, data, totals, "infinitepay_checkout", claims)
    payment = Payment(
        order=order,
        checkout_token=checkout_token(),
        provider="infinitepay",
        method="checkout",
    )
    db.add(payment)
    db.flush()
    payload = {
        "order_nsu": order.id,
        "redirect_url": public_url(request, "checkout"),
        "webhook_url": public_url(request, "api/payments/webhook/infinitepay"),
        "items": [
            {
                "quantity": 1,
                "price": cents(totals["total"]),
                "description": f"Pedido {order.id} - VJ Semijoias",
            }
        ],
        "customer": {
            "name": order.customer_name,
            "email": order.customer_email,
            "phone_number": f'+55{"".join(filter(str.isdigit, order.customer_phone or ""))}',
        },
        "address": {
            "cep": "".join(filter(str.isdigit, order.address_zip or "")),
            "street": order.address_street or "",
            "neighborhood": order.address_neighborhood or "",
            "number": order.address_number or "",
            "complement": order.address_complement or "",
        },
    }
    try:
        provider_order = infinitepay().create_link(payload)
        checkout_url = provider_order.get("url")
        if not checkout_url:
            raise InfinitePayError(
                "A InfinitePay não retornou o link de pagamento",
                details=provider_order,
            )
        db.commit()
    except InfinitePayError as exc:
        payment.status = "failed"
        payment.status_detail = str(exc)
        order.status = "failed"
        db.commit()
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "error": str(exc),
                "order_id": order.id,
                "details": exc.details,
            },
        )
    return {
        "order": order.to_dict(),
        "payment": payment.to_dict(),
        "checkout_url": checkout_url,
    }


@router.post("/infinitepay/confirm")
def confirm_infinitepay_payment(
    data: dict[str, Any] = Body(default_factory=dict),
    db: Session = Depends(get_db),
):
    if any(not data.get(field) for field in ["order_nsu", "transaction_nsu", "slug"]):
        raise HTTPException(status_code=400, detail="Dados de confirmação incompletos")
    payment = db.scalar(
        select(Payment).where(
            Payment.order_id == data["order_nsu"],
            Payment.provider == "infinitepay",
        )
    )
    if not payment:
        raise HTTPException(status_code=404, detail="Pagamento não encontrado")
    try:
        provider_data = infinitepay().check_payment(
            data["order_nsu"], data["transaction_nsu"], data["slug"]
        )
        provider_data.update(
            {
                "transaction_nsu": data["transaction_nsu"],
                "slug": data["slug"],
                "capture_method": data.get("capture_method"),
            }
        )
        update_infinitepay_payment(payment, provider_data)
        db.commit()
    except (InfinitePayError, ValueError) as exc:
        return JSONResponse(
            status_code=getattr(exc, "status_code", 400),
            content={"error": str(exc), "details": getattr(exc, "details", None)},
        )
    return {"order": payment.order.to_dict(), "payment": payment.to_dict()}


@router.post("/webhook/infinitepay")
def infinitepay_webhook(
    data: dict[str, Any] = Body(default_factory=dict),
    db: Session = Depends(get_db),
):
    order_nsu = data.get("order_nsu")
    transaction_nsu = data.get("transaction_nsu")
    slug = data.get("invoice_slug") or data.get("slug")
    if not order_nsu or not transaction_nsu or not slug:
        raise HTTPException(status_code=400, detail="Webhook incompleto")
    payment = db.scalar(
        select(Payment).where(
            Payment.order_id == order_nsu,
            Payment.provider == "infinitepay",
        )
    )
    if not payment:
        raise HTTPException(status_code=404, detail="Pedido não encontrado")
    try:
        provider_data = infinitepay().check_payment(order_nsu, transaction_nsu, slug)
        provider_data.update(
            {
                "transaction_nsu": transaction_nsu,
                "slug": slug,
                "capture_method": data.get("capture_method"),
            }
        )
        update_infinitepay_payment(payment, provider_data)
        db.commit()
    except (InfinitePayError, ValueError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"received": True}
