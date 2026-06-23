import json

from sqlalchemy.orm import Session

from backend.models import Order, OrderEvent


ORDER_STATUS_MESSAGES = {
    "pending": "Pedido criado",
    "paid": "Pagamento aprovado",
    "processing": "Pedido em separacao",
    "shipped": "Pedido enviado",
    "delivered": "Pedido entregue",
    "canceled": "Pedido cancelado",
    "failed": "Pedido falhou",
}


def order_status_message(status: str) -> str:
    return ORDER_STATUS_MESSAGES.get(status, f"Status atualizado para {status}")


def record_order_event(
    db: Session,
    order: Order,
    *,
    event_type: str,
    status: str | None = None,
    message: str | None = None,
    actor_user_id: int | None = None,
    metadata: dict | None = None,
) -> OrderEvent:
    event = OrderEvent(
        order=order,
        event_type=event_type,
        status=status,
        message=message or (order_status_message(status) if status else event_type),
        actor_user_id=actor_user_id,
        metadata_json=json.dumps(metadata or {}, ensure_ascii=False),
    )
    db.add(event)
    return event


def record_status_event(
    db: Session,
    order: Order,
    status: str,
    *,
    actor_user_id: int | None = None,
    metadata: dict | None = None,
) -> OrderEvent:
    return record_order_event(
        db,
        order,
        event_type=f"order.status.{status}",
        status=status,
        actor_user_id=actor_user_id,
        metadata=metadata,
    )
