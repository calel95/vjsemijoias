from typing import Any

from fastapi import APIRouter, Body, Depends, HTTPException, Query, Request
from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.auth import admin_claims
from backend.database import get_db
from backend.models import Product, StockMovement
from backend.routers.vj_admin_common import admin_user_id
from backend.services.admin_audit import record_vj_admin_audit
from backend.services.common import get_or_404
from backend.services.stock import create_stock_movement
from backend.services.vj_products import products_statement


router = APIRouter(prefix="/api/vj-admin", tags=["VJ Admin"])


@router.get("/estoque")
def list_stock(
    produto: str = Query(default=""),
    search: str = Query(default=""),
    categoria: str = Query(default=""),
    fornecedor_id: int | None = Query(default=None),
    status: str = Query(default=""),
    _claims=Depends(admin_claims),
    db: Session = Depends(get_db),
):
    try:
        statement = products_statement(
            search=search or produto,
            categoria=categoria,
            fornecedor_id=fornecedor_id,
            status=status,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    products = db.scalars(statement).unique().all()
    return [product.to_dict() for product in products]


@router.get("/produtos/{product_id}/estoque")
def get_product_stock(
    product_id: int,
    _claims=Depends(admin_claims),
    db: Session = Depends(get_db),
):
    product = get_or_404(db, Product, product_id)
    movements = db.scalars(
        select(StockMovement)
        .where(StockMovement.produto_id == product_id)
        .order_by(StockMovement.created_at.desc(), StockMovement.id.desc())
    ).all()
    return {
        "produto": product.to_dict(),
        "movimentacoes": [movement.to_dict() for movement in movements],
    }


@router.post("/produtos/{product_id}/estoque/movimentar", status_code=201)
def move_product_stock(
    product_id: int,
    request: Request,
    data: dict[str, Any] = Body(default_factory=dict),
    claims=Depends(admin_claims),
    db: Session = Depends(get_db),
):
    product = db.scalar(select(Product).where(Product.id == product_id).with_for_update())
    if product is None:
        raise HTTPException(status_code=404, detail="Produto nao encontrado")
    actor_id = admin_user_id(claims)
    try:
        movement = create_stock_movement(
            db,
            product,
            tipo=data.get("tipo"),
            quantidade=data.get("quantidade"),
            motivo=data.get("motivo"),
            observacoes=data.get("observacoes"),
            created_by_id=actor_id,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    product.updated_by_id = actor_id
    db.flush()
    record_vj_admin_audit(
        db,
        request,
        admin_user_id=actor_id,
        action="estoque_movimentado",
        resource="estoque",
        resource_id=movement.id,
        metadata={
            "produto_id": product.id,
            "codigo": product.codigo,
            "tipo": movement.tipo,
            "quantidade": movement.quantidade,
            "saldo_anterior": movement.saldo_anterior,
            "saldo_atual": movement.saldo_atual,
        },
    )
    db.commit()
    return {
        "produto": product.to_dict(),
        "movimentacao": movement.to_dict(),
    }