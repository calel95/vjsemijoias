from typing import Any

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from backend.models import Product, Supplier
from backend.services.common import normalize_bool
from backend.services.pricing import DEFAULT_MARKUP, DEFAULT_PACKAGING_COST, apply_pricing
from backend.services.stock import normalize_stock_quantity, sync_stock_status
from backend.services.validation import clean_text, normalize_money_decimal


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


def apply_supplier_fields(supplier: Supplier, cleaned: dict[str, Any]) -> None:
    for field, value in cleaned.items():
        setattr(supplier, field, value)


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
            cleaned[field] = normalize_optional_text(
                data.get(field), field=field, max_length=max_length
            )
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
        raise ValueError("Fornecedor nao encontrado")


def build_product(cleaned: dict[str, Any], *, actor_id: int | None = None) -> Product:
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
    return product


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
            raise ValueError("Status invalido")
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


def publish_product(product: Product, *, actor_id: int | None = None) -> None:
    product.status = "publicado"
    product.publicado = True
    product.is_active = True
    product.updated_by_id = actor_id
    sync_stock_status(product)


def unpublish_product(product: Product, *, actor_id: int | None = None) -> None:
    product.status = "rascunho"
    product.publicado = False
    product.is_active = False
    product.updated_by_id = actor_id
    sync_stock_status(product)


def deactivate_product(product: Product, confirmation, *, actor_id: int | None = None) -> None:
    confirmation = clean_text(
        confirmation,
        field="confirm",
        max_length=80,
        required=False,
    )
    if confirmation.upper() not in {"INATIVAR", str(product.codigo or "").upper()}:
        raise ValueError("Confirmacao invalida para inativar produto")
    product.status = "inativo"
    product.publicado = False
    product.is_active = False
    product.updated_by_id = actor_id
    sync_stock_status(product)
