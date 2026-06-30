from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from backend.models import Customer, VJAdminOrder
from backend.models.base import decimal_to_float
from backend.services.validation import clean_text, normalize_email, normalize_phone, validate_cpf

CUSTOMER_STATUSES = {"ativo", "inativo"}


def normalize_customer_status(value, *, default="ativo") -> str:
    status = clean_text(value or default, field="status", max_length=30, required=True).lower()
    if status not in CUSTOMER_STATUSES:
        raise ValueError("Status de cliente invalido")
    return status


def normalize_instagram(value) -> str | None:
    instagram = clean_text(value, field="instagram", max_length=120, required=False)
    if not instagram:
        return None
    return instagram.lstrip("@").lower() or None


def normalize_state(value) -> str | None:
    state = clean_text(value, field="estado", max_length=2, required=False).upper()
    return state or None


def normalize_optional_text(value, *, field: str, max_length: int, allow_newlines=False) -> str | None:
    text = clean_text(value, field=field, max_length=max_length, required=False, allow_newlines=allow_newlines)
    return text or None


def normalize_birth_date(value) -> date | None:
    if value in (None, ""):
        return None
    if isinstance(value, date) and not isinstance(value, datetime):
        return value
    if isinstance(value, datetime):
        return value.date()
    try:
        return date.fromisoformat(str(value)[:10])
    except ValueError as exc:
        raise ValueError("data_nascimento invalida") from exc


def customer_payload(data: dict[str, Any], *, partial=False) -> dict[str, Any]:
    payload: dict[str, Any] = {}
    if not partial or "nome" in data:
        payload["nome"] = clean_text(data.get("nome"), field="nome", max_length=200, required=not partial)
    if not partial or "whatsapp" in data:
        payload["whatsapp"] = normalize_phone(data.get("whatsapp"), required=False) or None
    if not partial or "email" in data:
        payload["email"] = normalize_email(data.get("email"), required=False) or None
    if not partial or "cpf" in data:
        payload["cpf"] = validate_cpf(data.get("cpf"), required=False) or None
    if not partial or "instagram" in data:
        payload["instagram"] = normalize_instagram(data.get("instagram"))
    if not partial or "cidade" in data:
        payload["cidade"] = normalize_optional_text(data.get("cidade"), field="cidade", max_length=120)
    if not partial or "estado" in data:
        payload["estado"] = normalize_state(data.get("estado"))
    if not partial or "data_nascimento" in data:
        payload["data_nascimento"] = normalize_birth_date(data.get("data_nascimento"))
    if not partial or "observacoes" in data:
        payload["observacoes"] = normalize_optional_text(
            data.get("observacoes"), field="observacoes", max_length=2000, allow_newlines=True
        )
    if not partial or "origem" in data:
        payload["origem"] = normalize_optional_text(data.get("origem"), field="origem", max_length=120)
    if not partial or "status" in data:
        payload["status"] = normalize_customer_status(data.get("status"), default="ativo")
    if partial:
        payload = {key: value for key, value in payload.items() if key in data}
    return payload


def apply_customer_fields(customer: Customer, payload: dict[str, Any], *, actor_id: int | None):
    for field, value in payload.items():
        setattr(customer, field, value)
    customer.updated_by_id = actor_id
    return customer


def create_customer(db: Session, data: dict[str, Any], *, actor_id: int | None) -> Customer:
    customer = Customer(**customer_payload(data), created_by_id=actor_id, updated_by_id=actor_id)
    db.add(customer)
    return customer


def update_customer(db: Session, customer: Customer, data: dict[str, Any], *, actor_id: int | None) -> Customer:
    return apply_customer_fields(customer, customer_payload(data, partial=True), actor_id=actor_id)


def deactivate_customer(customer: Customer, *, actor_id: int | None) -> Customer:
    customer.status = "inativo"
    customer.updated_by_id = actor_id
    return customer


def customers_statement(*, search="", status="", cidade="", origem=""):
    statement = select(Customer)
    filters = []
    search = (search or "").strip().lower()
    if search:
        pattern = f"%{search}%"
        filters.append(
            or_(
                func.lower(Customer.nome).like(pattern),
                func.lower(Customer.whatsapp).like(pattern),
                func.lower(Customer.email).like(pattern),
                func.lower(Customer.instagram).like(pattern),
            )
        )
    status = (status or "").strip().lower()
    if status:
        if status not in CUSTOMER_STATUSES:
            raise ValueError("Status de cliente invalido")
        filters.append(Customer.status == status)
    cidade = (cidade or "").strip().lower()
    if cidade:
        filters.append(func.lower(Customer.cidade) == cidade)
    origem = (origem or "").strip().lower()
    if origem:
        filters.append(func.lower(Customer.origem) == origem)
    if filters:
        statement = statement.where(*filters)
    return statement.order_by(Customer.nome, Customer.id)


def customer_or_error(db: Session, customer_id: int) -> Customer:
    customer = db.get(Customer, customer_id)
    if customer is None:
        raise ValueError("Cliente nao encontrado")
    return customer


def active_customer_or_error(db: Session, customer_id: int) -> Customer:
    customer = customer_or_error(db, customer_id)
    if customer.status != "ativo":
        raise ValueError("Cliente inativo nao pode ser usado em novo pedido")
    return customer


def customer_order_summary(orders: list[VJAdminOrder]) -> dict[str, Any]:
    confirmed = [order for order in orders if order.status == "confirmado"]
    total = sum((order.total or Decimal("0.00") for order in confirmed), Decimal("0.00"))
    count = len(confirmed)
    ticket = (total / count).quantize(Decimal("0.01")) if count else Decimal("0.00")
    latest = max((order.updated_at or order.created_at for order in confirmed), default=None)
    return {
        "total_gasto": decimal_to_float(total),
        "quantidade_pedidos": count,
        "ticket_medio": decimal_to_float(ticket),
        "ultima_compra": latest.isoformat() if latest else None,
    }


def customer_orders_payload(db: Session, customer: Customer) -> dict[str, Any]:
    orders = db.scalars(
        select(VJAdminOrder)
        .where(VJAdminOrder.customer_id == customer.id)
        .order_by(VJAdminOrder.id.desc())
    ).unique().all()
    return {
        "cliente": customer.to_dict(),
        "pedidos": [order.to_dict() for order in orders],
        "metricas": customer_order_summary(orders),
    }