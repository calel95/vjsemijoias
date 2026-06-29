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
from backend.services.common import get_or_404, normalize_bool
from backend.services.pricing import (
    CALCULATED_PRICE_FIELDS,
    DEFAULT_MARKUP,
    DEFAULT_PACKAGING_COST,
    apply_pricing,
)
from backend.services.product_media import replace_product_gallery, store_admin_gallery_images
from backend.services.stock import create_stock_movement, normalize_stock_quantity, sync_stock_status
from backend.services.validation import clean_text, normalize_money_decimal
from backend.services.vj_orders import (
    cancel_vj_admin_order,
    confirm_vj_admin_order,
    create_vj_admin_order,
    update_vj_admin_order,
)


router = APIRouter(prefix="/api/vj-admin", tags=["VJ Admin"])
ACTIVE_PRODUCT_STATUSES = {"publicado", "ativo"}
PRODUCT_STATUSES = {"rascunho", "publicado", "ativo", "inativo"}
CSV_FIELDS = [
    "id",
    "codigo",
    "nome",
    "categoria",
    "fornecedor",
    "material",
    "banho",
    "cor",
    "custo_peca",
    "custo_embalagem",
    "custo_total",
    "markup",
    "preco_pix",
    "preco_debito",
    "preco_credito_vista",
    "preco_credito_2x",
    "preco_credito_3x",
    "preco_credito_4x",
    "preco_credito_5x",
    "preco_credito_6x",
    "preco_credito_7x",
    "preco_credito_8x",
    "preco_credito_9x",
    "preco_credito_10x",
    "preco_credito_11x",
    "preco_credito_12x",
    "margem_pix",
    "lucro_pix",
    "estoque",
    "saldo_estoque",
    "status",
    "publicado",
    "created_at",
    "updated_at",
    "created_by",
    "updated_by",
]


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
def normalize_code(value, *, required=True):
    code = clean_text(value, field="codigo", max_length=80, required=required)
    return code.upper() or None


def normalize_optional_text(value, *, field, max_length=200):
    return clean_text(value, field=field, max_length=max_length, required=False) or None


def normalize_category_filter(value: str):
    category = clean_text(value, field="categoria", max_length=50, required=False)
    return category.lower().replace(" ", "-") if category else ""


def normalize_status(value, *, default="rascunho"):
    status = clean_text(value or default, field="status", max_length=30, required=True).lower()
    if status not in PRODUCT_STATUSES:
        raise ValueError("status deve ser rascunho, publicado, ativo ou inativo")
    return status


def product_is_public(status: str, publicado: bool):
    return bool(publicado) and status in ACTIVE_PRODUCT_STATUSES


def supplier_payload(data: dict[str, Any], *, partial=False):
    cleaned = {}
    if "nome" in data or not partial:
        cleaned["nome"] = clean_text(
            data.get("nome"),
            field="nome",
            max_length=200,
            required=not partial,
        )
    for field, max_length in {
        "whatsapp": 30,
        "instagram": 120,
        "site": 255,
        "observacoes": 2000,
    }.items():
        if field in data:
            cleaned[field] = normalize_optional_text(
                data.get(field),
                field=field,
                max_length=max_length,
            )
    return cleaned


def product_payload(data: dict[str, Any], *, partial=False):
    cleaned: dict[str, Any] = {}
    if "codigo" in data or not partial:
        cleaned["codigo"] = normalize_code(data.get("codigo"), required=not partial)
    if "nome" in data or "name" in data or not partial:
        cleaned["name"] = clean_text(
            data.get("nome", data.get("name")),
            field="nome",
            max_length=200,
            required=not partial,
        )
    if "categoria" in data or "category" in data or not partial:
        category = clean_text(
            data.get("categoria", data.get("category")),
            field="categoria",
            max_length=50,
            required=not partial,
        )
        cleaned["category"] = category.lower().replace(" ", "-")
        cleaned["categoryName"] = category.capitalize()
    for field, max_length in {
        "material": 120,
        "banho": 120,
        "cor": 80,
    }.items():
        if field in data:
            cleaned[field] = normalize_optional_text(data.get(field), field=field, max_length=max_length)
    if "descricao" in data or "description" in data or not partial:
        cleaned["description"] = clean_text(
            data.get("descricao", data.get("description")),
            field="descricao",
            max_length=2000,
            required=False,
            allow_newlines=True,
        )
    if "imagem_url" in data or "image" in data:
        cleaned["image"] = normalize_optional_text(
            data.get("imagem_url", data.get("image")),
            field="imagem_url",
            max_length=2000,
        )
    if "estoque" in data or "stock_quantity" in data or not partial:
        cleaned["stock_quantity"] = normalize_stock_quantity(
            data.get("estoque", data.get("stock_quantity", 0))
        )
    if "fornecedor_id" in data:
        supplier_id = data.get("fornecedor_id")
        cleaned["fornecedor_id"] = int(supplier_id) if supplier_id not in (None, "") else None
    for field in ("custo_peca", "custo_embalagem", "markup"):
        if field in data or (not partial and field == "custo_peca"):
            cleaned[field] = data.get(field)
    if not partial and "custo_embalagem" not in cleaned:
        cleaned["custo_embalagem"] = DEFAULT_PACKAGING_COST
    if not partial and "markup" not in cleaned:
        cleaned["markup"] = DEFAULT_MARKUP
    status_value = data.get("status") if "status" in data else None
    if "status" in data or "publicado" in data or not partial:
        status = normalize_status(status_value, default="rascunho")
        publicado = normalize_bool(data.get("publicado"), status in ACTIVE_PRODUCT_STATUSES)
        if publicado and status not in ACTIVE_PRODUCT_STATUSES:
            status = "publicado"
        cleaned["status"] = status
        cleaned["publicado"] = product_is_public(status, publicado)
    return cleaned


def ensure_supplier_exists(db: Session, supplier_id: int | None):
    if supplier_id is None:
        return
    if db.get(Supplier, supplier_id) is None:
        raise HTTPException(status_code=400, detail="Fornecedor nao encontrado")


def apply_product_fields(product: Product, cleaned: dict[str, Any]):
    for source, target in {
        "name": "name",
        "category": "category",
        "categoryName": "categoryName",
        "description": "description",
        "codigo": "codigo",
        "fornecedor_id": "fornecedor_id",
        "material": "material",
        "banho": "banho",
        "cor": "cor",
        "status": "status",
        "publicado": "publicado",
        "stock_quantity": "stock_quantity",
    }.items():
        if source in cleaned:
            setattr(product, target, cleaned[source])
    if "codigo" in cleaned:
        product.sku = cleaned["codigo"]
    if "image" in cleaned:
        product.image = cleaned["image"]
    if "publicado" in cleaned or "status" in cleaned:
        product.is_active = product_is_public(product.status, product.publicado)
    sync_stock_status(product)


def calculate_product_prices(product: Product, cleaned: dict[str, Any]):
    custo_peca = cleaned.get("custo_peca", product.custo_peca)
    custo_embalagem = cleaned.get("custo_embalagem", product.custo_embalagem)
    markup = cleaned.get("markup", product.markup)
    apply_pricing(
        product,
        custo_peca=custo_peca,
        custo_embalagem=custo_embalagem,
        markup=markup,
    )


def products_statement(
    *,
    search: str = "",
    categoria: str = "",
    fornecedor_id: int | None = None,
    status: str = "",
):
    statement = select(Product)
    filters = []
    search = search.strip().lower()
    if search:
        pattern = f"%{search}%"
        filters.append(
            or_(
                func.lower(Product.name).like(pattern),
                func.lower(Product.codigo).like(pattern),
            )
        )
    categoria = normalize_category_filter(categoria)
    if categoria:
        filters.append(Product.category == categoria)
    if fornecedor_id is not None:
        filters.append(Product.fornecedor_id == fornecedor_id)
    status = status.strip().lower()
    if status:
        if status == "publicado":
            filters.append(Product.status.in_(["publicado", "ativo"]))
            filters.append(Product.publicado.is_(True))
        elif status in PRODUCT_STATUSES:
            filters.append(Product.status == status)
        else:
            raise HTTPException(status_code=400, detail="Status invalido")
    if filters:
        statement = statement.where(*filters)
    return statement.order_by(Product.id.desc())


def product_csv_row(product: Product):
    data = product.to_dict()
    return {
        **{field: data.get(field) for field in CSV_FIELDS},
        "fornecedor": (data.get("fornecedor") or {}).get("nome") or "",
        "created_by": (data.get("created_by") or {}).get("email") or "",
        "updated_by": (data.get("updated_by") or {}).get("email") or "",
    }


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
    for field, value in cleaned.items():
        setattr(supplier, field, value)
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
    products = db.scalars(
        products_statement(
            search=search,
            categoria=categoria,
            fornecedor_id=fornecedor_id,
            status=status,
        )
    ).unique().all()
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
    products = db.scalars(
        products_statement(
            search=search,
            categoria=categoria,
            fornecedor_id=fornecedor_id,
            status=status,
        )
    ).unique().all()
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
    products = db.scalars(
        products_statement(
            search=search or produto,
            categoria=categoria,
            fornecedor_id=fornecedor_id,
            status=status,
        )
    ).unique().all()
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
    actor_id = admin_user_id(claims)
    product = Product(
        name=cleaned["name"],
        category=cleaned["category"],
        categoryName=cleaned["categoryName"],
        price=normalize_money_decimal(0, field="price"),
        codigo=cleaned["codigo"],
        sku=cleaned["codigo"],
        fornecedor_id=cleaned.get("fornecedor_id"),
        material=cleaned.get("material"),
        banho=cleaned.get("banho"),
        cor=cleaned.get("cor"),
        image=cleaned.get("image"),
        icon="\U0001F48E",
        status=cleaned["status"],
        publicado=cleaned["publicado"],
        is_active=product_is_public(cleaned["status"], cleaned["publicado"]),
        stock_quantity=cleaned.get("stock_quantity", 0),
        low_stock_alert=1,
        description=cleaned.get("description") or "",
        features="[]",
        custom=True,
        created_by_id=actor_id,
        updated_by_id=actor_id,
    )
    calculate_product_prices(product, cleaned)
    sync_stock_status(product)
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
    product.status = "publicado"
    product.publicado = True
    product.is_active = True
    product.updated_by_id = admin_user_id(claims)
    sync_stock_status(product)
    db.commit()
    return product.to_dict()


@router.post("/produtos/{product_id}/despublicar")
def unpublish_product(
    product_id: int,
    claims=Depends(admin_claims),
    db: Session = Depends(get_db),
):
    product = get_or_404(db, Product, product_id)
    product.status = "rascunho"
    product.publicado = False
    product.is_active = False
    product.updated_by_id = admin_user_id(claims)
    sync_stock_status(product)
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
    confirmation = clean_text(data.get("confirm"), field="confirm", max_length=80, required=False)
    if confirmation.upper() not in {"INATIVAR", str(product.codigo or "").upper()}:
        raise HTTPException(status_code=400, detail="Confirmacao invalida para inativar produto")
    product.status = "inativo"
    product.publicado = False
    product.is_active = False
    product.updated_by_id = admin_user_id(claims)
    sync_stock_status(product)
    db.commit()
    return product.to_dict()



