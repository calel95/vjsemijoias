import csv
from io import StringIO
from typing import Any

from fastapi import APIRouter, Body, Depends, HTTPException, Query, Response
from sqlalchemy import func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from backend.auth import admin_claims
from backend.database import get_db
from backend.models import Product, StockMovement, Supplier, VJAdminOrder
from backend.services.common import get_or_404
from backend.services.pricing import CALCULATED_PRICE_FIELDS, DEFAULT_MARKUP, DEFAULT_PACKAGING_COST
from backend.services.product_media import replace_product_gallery, store_admin_gallery_images
from backend.services.stock import create_stock_movement
from backend.services.vj_orders import (
    cancel_vj_admin_order,
    confirm_vj_admin_order,
    create_vj_admin_order,
    update_vj_admin_order,
)
from backend.services.vj_products import (
    CSV_FIELDS,
    apply_product_fields,
    apply_supplier_fields,
    build_product,
    calculate_product_prices,
    deactivate_product as deactivate_vj_product,
    ensure_supplier_exists,
    product_csv_row,
    product_payload,
    products_statement,
    publish_product as publish_vj_product,
    supplier_payload,
    unpublish_product as unpublish_vj_product,
)


router = APIRouter(prefix="/api/vj-admin", tags=["VJ Admin"])


def admin_user_id(claims) -> int | None:
    try:
        return int(claims.get("sub")) if claims and claims.get("sub") else None
    except (TypeError, ValueError):
        return None


def locked_order_or_404(db: Session, order_id: int) -> VJAdminOrder:
    order = db.scalar(select(VJAdminOrder).where(VJAdminOrder.id == order_id).with_for_update())
    if order is None:
        raise HTTPException(status_code=404, detail="Pedido nao encontrado")
    return order


@router.get("/pricing/defaults")
def pricing_defaults(_claims=Depends(admin_claims)):
    from backend.services.pricing import PAYMENT_FEES

    return {
        "markup": float(DEFAULT_MARKUP),
        "custo_embalagem": float(DEFAULT_PACKAGING_COST),
        "taxas": {field: float(value) for field, value in PAYMENT_FEES.items()},
        "campos_calculados": list(CALCULATED_PRICE_FIELDS),
    }


@router.get("/fornecedores")
def list_suppliers(
    _claims=Depends(admin_claims),
    db: Session = Depends(get_db),
):
    suppliers = db.scalars(select(Supplier).order_by(Supplier.nome, Supplier.id)).all()
    return [supplier.to_dict() for supplier in suppliers]


@router.post("/fornecedores", status_code=201)
def create_supplier(
    data: dict[str, Any] = Body(default_factory=dict),
    _claims=Depends(admin_claims),
    db: Session = Depends(get_db),
):
    try:
        cleaned = supplier_payload(data)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    supplier = Supplier(**cleaned)
    db.add(supplier)
    db.commit()
    return supplier.to_dict()


@router.put("/fornecedores/{supplier_id}")
def update_supplier(
    supplier_id: int,
    data: dict[str, Any] = Body(default_factory=dict),
    _claims=Depends(admin_claims),
    db: Session = Depends(get_db),
):
    supplier = get_or_404(db, Supplier, supplier_id)
    try:
        cleaned = supplier_payload(data, partial=True)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    apply_supplier_fields(supplier, cleaned)
    db.commit()
    return supplier.to_dict()


@router.get("/produtos")
def list_products(
    search: str = Query(default=""),
    categoria: str = Query(default=""),
    fornecedor_id: int | None = Query(default=None),
    status: str = Query(default=""),
    _claims=Depends(admin_claims),
    db: Session = Depends(get_db),
):
    try:
        statement = products_statement(
            search=search,
            categoria=categoria,
            fornecedor_id=fornecedor_id,
            status=status,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    products = db.scalars(statement).unique().all()
    return [product.to_dict() for product in products]


@router.get("/produtos/export.csv")
def export_products_csv(
    search: str = Query(default=""),
    categoria: str = Query(default=""),
    fornecedor_id: int | None = Query(default=None),
    status: str = Query(default=""),
    _claims=Depends(admin_claims),
    db: Session = Depends(get_db),
):
    try:
        statement = products_statement(
            search=search,
            categoria=categoria,
            fornecedor_id=fornecedor_id,
            status=status,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    products = db.scalars(statement).unique().all()
    output = StringIO()
    output.write("\ufeff")
    writer = csv.DictWriter(output, fieldnames=CSV_FIELDS, extrasaction="ignore")
    writer.writeheader()
    for product in products:
        writer.writerow(product_csv_row(product))
    return Response(
        content=output.getvalue(),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": 'attachment; filename="vj-admin-produtos.csv"'},
    )



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
    db.commit()
    return {
        "produto": product.to_dict(),
        "movimentacao": movement.to_dict(),
    }


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

@router.get("/produtos/{product_id}")
def get_admin_product(
    product_id: int,
    _claims=Depends(admin_claims),
    db: Session = Depends(get_db),
):
    return get_or_404(db, Product, product_id).to_dict()


@router.post("/produtos", status_code=201)
def create_product(
    data: dict[str, Any] = Body(default_factory=dict),
    claims=Depends(admin_claims),
    db: Session = Depends(get_db),
):
    try:
        cleaned = product_payload(data)
        ensure_supplier_exists(db, cleaned.get("fornecedor_id"))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    if db.scalar(select(Product.id).where(Product.codigo == cleaned["codigo"])):
        raise HTTPException(status_code=409, detail="Codigo ja cadastrado")
    product = build_product(cleaned, actor_id=admin_user_id(claims))
    db.add(product)
    db.flush()
    if product.image:
        images = store_admin_gallery_images(product, [product.image])
        replace_product_gallery(product, images)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(status_code=409, detail="Codigo ja cadastrado") from exc
    return product.to_dict()


@router.put("/produtos/{product_id}")
def update_product(
    product_id: int,
    data: dict[str, Any] = Body(default_factory=dict),
    claims=Depends(admin_claims),
    db: Session = Depends(get_db),
):
    product = get_or_404(db, Product, product_id)
    try:
        cleaned = product_payload(data, partial=True)
        ensure_supplier_exists(db, cleaned.get("fornecedor_id"))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    if cleaned.get("codigo") and db.scalar(
        select(Product.id).where(Product.codigo == cleaned["codigo"], Product.id != product_id)
    ):
        raise HTTPException(status_code=409, detail="Codigo ja cadastrado")
    cleaned.pop("stock_quantity", None)
    apply_product_fields(product, cleaned)
    product.updated_by_id = admin_user_id(claims)
    if any(field in cleaned for field in ("custo_peca", "custo_embalagem", "markup")):
        calculate_product_prices(product, cleaned)
    if "image" in cleaned:
        images = store_admin_gallery_images(product, [product.image] if product.image else [])
        replace_product_gallery(product, images)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(status_code=409, detail="Codigo ja cadastrado") from exc
    return product.to_dict()


@router.post("/produtos/{product_id}/publicar")
def publish_product(
    product_id: int,
    claims=Depends(admin_claims),
    db: Session = Depends(get_db),
):
    product = get_or_404(db, Product, product_id)
    publish_vj_product(product, actor_id=admin_user_id(claims))
    db.commit()
    return product.to_dict()


@router.post("/produtos/{product_id}/despublicar")
def unpublish_product(
    product_id: int,
    claims=Depends(admin_claims),
    db: Session = Depends(get_db),
):
    product = get_or_404(db, Product, product_id)
    unpublish_vj_product(product, actor_id=admin_user_id(claims))
    db.commit()
    return product.to_dict()


@router.post("/produtos/{product_id}/inativar")
def deactivate_product(
    product_id: int,
    data: dict[str, Any] = Body(default_factory=dict),
    claims=Depends(admin_claims),
    db: Session = Depends(get_db),
):
    product = get_or_404(db, Product, product_id)
    try:
        deactivate_vj_product(product, data.get("confirm"), actor_id=admin_user_id(claims))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    db.commit()
    return product.to_dict()



