import csv
from io import StringIO
from typing import Any

from fastapi import APIRouter, Body, Depends, HTTPException, Query, Request, Response
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session, selectinload

from backend.auth import admin_claims
from backend.database import get_db
from backend.models import VJAdminOrder, VJAdminOrderItem
from backend.routers.vj_admin_common import admin_user_id
from backend.services.admin_audit import record_vj_admin_audit
from backend.services.vj_orders import (
    cancel_vj_admin_order,
    confirm_vj_admin_order,
    create_vj_admin_order,
    update_vj_admin_order,
)


router = APIRouter(prefix="/api/vj-admin", tags=["VJ Admin"])

ORDER_CSV_FIELDS = [
    "id",
    "status",
    "customer_id",
    "cliente_nome",
    "cliente_whatsapp",
    "forma_pagamento",
    "parcelas",
    "subtotal",
    "desconto_total",
    "taxa_pagamento",
    "total",
    "lucro_estimado",
    "margem_estimada",
    "quantidade_itens",
    "produtos",
    "created_at",
    "updated_at",
    "created_by",
    "updated_by",
]


def order_load_options():
    return (
        selectinload(VJAdminOrder.items).selectinload(VJAdminOrderItem.produto),
        selectinload(VJAdminOrder.customer),
        selectinload(VJAdminOrder.created_by),
        selectinload(VJAdminOrder.updated_by),
    )


def order_statement():
    return select(VJAdminOrder).options(*order_load_options())


def filtered_order_statement(*, status: str = "", search: str = ""):
    statement = order_statement()
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
    return statement.order_by(VJAdminOrder.id.desc())


def locked_order_or_404(db: Session, order_id: int) -> VJAdminOrder:
    order = db.scalar(order_statement().where(VJAdminOrder.id == order_id).with_for_update())
    if order is None:
        raise HTTPException(status_code=404, detail="Pedido nao encontrado")
    return order


def order_csv_row(order: VJAdminOrder):
    data = order.to_dict()
    products = []
    quantity = 0
    for item in order.items:
        quantity += int(item.quantidade or 0)
        product = item.produto
        label = product.codigo if product and product.codigo else str(item.produto_id)
        products.append(f"{label} x{item.quantidade}")
    return {
        **{field: data.get(field) for field in ORDER_CSV_FIELDS},
        "quantidade_itens": quantity,
        "produtos": " | ".join(products),
        "created_by": (data.get("created_by") or {}).get("email") or "",
        "updated_by": (data.get("updated_by") or {}).get("email") or "",
    }


@router.get("/pedidos")
def list_orders(
    status: str = Query(default=""),
    search: str = Query(default=""),
    _claims=Depends(admin_claims),
    db: Session = Depends(get_db),
):
    orders = db.scalars(filtered_order_statement(status=status, search=search)).unique().all()
    return [order.to_dict() for order in orders]


@router.get("/pedidos/export.csv")
def export_orders_csv(
    status: str = Query(default=""),
    search: str = Query(default=""),
    _claims=Depends(admin_claims),
    db: Session = Depends(get_db),
):
    output = StringIO()
    output.write("\ufeff")
    writer = csv.DictWriter(output, fieldnames=ORDER_CSV_FIELDS, extrasaction="ignore")
    writer.writeheader()
    for order in db.scalars(filtered_order_statement(status=status, search=search)).unique().all():
        writer.writerow(order_csv_row(order))
    return Response(
        content=output.getvalue(),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": 'attachment; filename="vj-admin-pedidos.csv"'},
    )


@router.get("/pedidos/{order_id}")
def get_order(
    order_id: int,
    _claims=Depends(admin_claims),
    db: Session = Depends(get_db),
):
    order = db.scalar(order_statement().where(VJAdminOrder.id == order_id))
    if order is None:
        raise HTTPException(status_code=404, detail="Pedido nao encontrado")
    return order.to_dict()


@router.post("/pedidos", status_code=201)
def create_order(
    request: Request,
    data: dict[str, Any] = Body(default_factory=dict),
    claims=Depends(admin_claims),
    db: Session = Depends(get_db),
):
    actor_id = admin_user_id(claims)
    try:
        order = create_vj_admin_order(db, data, actor_id=actor_id)
        db.flush()
        record_vj_admin_audit(
            db,
            request,
            admin_user_id=actor_id,
            action="pedido_criado",
            resource="pedido",
            resource_id=order.id,
            metadata={"status": order.status, "total": float(order.total or 0), "itens": len(order.items)},
        )
        db.commit()
    except ValueError as exc:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return order.to_dict()


@router.put("/pedidos/{order_id}")
def update_order(
    order_id: int,
    request: Request,
    data: dict[str, Any] = Body(default_factory=dict),
    claims=Depends(admin_claims),
    db: Session = Depends(get_db),
):
    order = locked_order_or_404(db, order_id)
    actor_id = admin_user_id(claims)
    try:
        update_vj_admin_order(db, order, data, actor_id=actor_id)
        db.flush()
        record_vj_admin_audit(
            db,
            request,
            admin_user_id=actor_id,
            action="pedido_atualizado",
            resource="pedido",
            resource_id=order.id,
            metadata={"status": order.status, "total": float(order.total or 0), "itens": len(order.items)},
        )
        db.commit()
    except ValueError as exc:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return order.to_dict()


@router.post("/pedidos/{order_id}/confirmar")
def confirm_order(
    order_id: int,
    request: Request,
    claims=Depends(admin_claims),
    db: Session = Depends(get_db),
):
    order = locked_order_or_404(db, order_id)
    actor_id = admin_user_id(claims)
    try:
        confirm_vj_admin_order(db, order, actor_id=actor_id)
        db.flush()
        record_vj_admin_audit(
            db,
            request,
            admin_user_id=actor_id,
            action="pedido_confirmado",
            resource="pedido",
            resource_id=order.id,
            metadata={"status": order.status, "total": float(order.total or 0), "itens": len(order.items)},
        )
        db.commit()
    except ValueError as exc:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return order.to_dict()


@router.post("/pedidos/{order_id}/cancelar")
def cancel_order(
    order_id: int,
    request: Request,
    claims=Depends(admin_claims),
    db: Session = Depends(get_db),
):
    order = locked_order_or_404(db, order_id)
    actor_id = admin_user_id(claims)
    try:
        cancel_vj_admin_order(db, order, actor_id=actor_id)
        db.flush()
        record_vj_admin_audit(
            db,
            request,
            admin_user_id=actor_id,
            action="pedido_cancelado",
            resource="pedido",
            resource_id=order.id,
            metadata={"status": order.status, "total": float(order.total or 0), "itens": len(order.items)},
        )
        db.commit()
    except ValueError as exc:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return order.to_dict()