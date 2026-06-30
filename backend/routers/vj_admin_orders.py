from typing import Any

from fastapi import APIRouter, Body, Depends, HTTPException, Query
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from backend.auth import admin_claims
from backend.database import get_db
from backend.models import VJAdminOrder
from backend.routers.vj_admin_common import admin_user_id
from backend.services.common import get_or_404
from backend.services.vj_orders import (
    cancel_vj_admin_order,
    confirm_vj_admin_order,
    create_vj_admin_order,
    update_vj_admin_order,
)


router = APIRouter(prefix="/api/vj-admin", tags=["VJ Admin"])


def locked_order_or_404(db: Session, order_id: int) -> VJAdminOrder:
    order = db.scalar(select(VJAdminOrder).where(VJAdminOrder.id == order_id).with_for_update())
    if order is None:
        raise HTTPException(status_code=404, detail="Pedido nao encontrado")
    return order


@router.get("/pedidos")
def list_orders(
    status: str = Query(default=""),
    search: str = Query(default=""),
    _claims=Depends(admin_claims),
    db: Session = Depends(get_db),
):
    statement = select(VJAdminOrder)
    filters = []
    status = status.strip().lower()
    if status:
        if status not in {"rascunho", "confirmado", "cancelado"}:
            raise HTTPException(status_code=400, detail="Status de pedido invalido")
        filters.append(VJAdminOrder.status == status)
    search = search.strip().lower()
    if search:
        pattern = f"%{search}%"
        filters.append(
            or_(
                func.lower(VJAdminOrder.cliente_nome).like(pattern),
                func.lower(VJAdminOrder.cliente_whatsapp).like(pattern),
            )
        )
    if filters:
        statement = statement.where(*filters)
    orders = db.scalars(statement.order_by(VJAdminOrder.id.desc())).unique().all()
    return [order.to_dict() for order in orders]


@router.get("/pedidos/{order_id}")
def get_order(
    order_id: int,
    _claims=Depends(admin_claims),
    db: Session = Depends(get_db),
):
    return get_or_404(db, VJAdminOrder, order_id).to_dict()


@router.post("/pedidos", status_code=201)
def create_order(
    data: dict[str, Any] = Body(default_factory=dict),
    claims=Depends(admin_claims),
    db: Session = Depends(get_db),
):
    try:
        order = create_vj_admin_order(db, data, actor_id=admin_user_id(claims))
        db.flush()
        db.commit()
    except ValueError as exc:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return order.to_dict()


@router.put("/pedidos/{order_id}")
def update_order(
    order_id: int,
    data: dict[str, Any] = Body(default_factory=dict),
    claims=Depends(admin_claims),
    db: Session = Depends(get_db),
):
    order = locked_order_or_404(db, order_id)
    try:
        update_vj_admin_order(db, order, data, actor_id=admin_user_id(claims))
        db.flush()
        db.commit()
    except ValueError as exc:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return order.to_dict()


@router.post("/pedidos/{order_id}/confirmar")
def confirm_order(
    order_id: int,
    claims=Depends(admin_claims),
    db: Session = Depends(get_db),
):
    order = locked_order_or_404(db, order_id)
    try:
        confirm_vj_admin_order(db, order, actor_id=admin_user_id(claims))
        db.flush()
        db.commit()
    except ValueError as exc:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return order.to_dict()


@router.post("/pedidos/{order_id}/cancelar")
def cancel_order(
    order_id: int,
    claims=Depends(admin_claims),
    db: Session = Depends(get_db),
):
    order = locked_order_or_404(db, order_id)
    try:
        cancel_vj_admin_order(db, order, actor_id=admin_user_id(claims))
        db.flush()
        db.commit()
    except ValueError as exc:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return order.to_dict()