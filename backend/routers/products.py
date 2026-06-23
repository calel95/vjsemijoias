import json
import secrets
import shutil
from pathlib import PurePosixPath
from typing import Any

from fastapi import APIRouter, Body, Depends, File, HTTPException, Query, Request, UploadFile
from sqlalchemy.exc import IntegrityError
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from backend.auth import admin_claims
from backend.config import IMPORT_UPLOAD_ROOT
from backend.database import get_db
from backend.models import Product, User
from backend.services.admin_security import record_admin_audit
from backend.services.common import get_or_404, normalize_bool
from backend.services.product_media import (
    normalize_stock_status,
    product_image_list,
    replace_product_gallery,
    store_admin_gallery_images,
)
from backend.services.storage import storage_status
from backend.services.stock import (
    normalize_low_stock_alert,
    normalize_sku,
    normalize_stock_quantity,
    sync_stock_status,
)
from backend.services.validation import clean_text, clean_text_list, normalize_money_decimal


router = APIRouter(prefix="/api")
IMPORT_UPLOAD_MAX_FILE_BYTES = 20 * 1024 * 1024
IMPORT_UPLOAD_MAX_TOTAL_BYTES = 250 * 1024 * 1024
IMPORT_UPLOAD_ALLOWED_EXTENSIONS = {".csv", ".json", ".jpg", ".jpeg", ".png", ".webp", ".gif"}
CATEGORY_ICONS = {
    "all": "\U0001F48E",
    "brincos": "\u2728",
    "colares": "\U0001F4FF",
    "pulseiras": "\u269C\ufe0f",
    "aneis": "\U0001F48D",
    "pingentes": "\U0001F52E",
    "chaveiros": "\U0001F511",
    "conjuntos": "\U0001F381",
}


def normalize_product_payload(data: dict[str, Any], *, partial=False):
    cleaned: dict[str, Any] = {}
    text_fields = {
        "name": (200, True),
        "category": (50, True),
        "categoryName": (50, False),
        "icon": (10, False),
        "badge": (20, False),
        "description": (1000, True),
    }
    for field, (max_length, required_on_create) in text_fields.items():
        if field in data or (required_on_create and not partial):
            cleaned[field] = clean_text(
                data.get(field),
                field=field,
                max_length=max_length,
                required=required_on_create and not partial,
            )

    if "categoryName" not in cleaned and "category" in cleaned:
        cleaned["categoryName"] = cleaned["category"].capitalize()
    if "price" in data or not partial:
        cleaned["price"] = normalize_money_decimal(data.get("price"), field="price")
    if "oldPrice" in data:
        cleaned["oldPrice"] = normalize_money_decimal(
            data.get("oldPrice"),
            field="oldPrice",
            required=False,
        )
    if "sku" in data:
        cleaned["sku"] = normalize_sku(data.get("sku"))
    if "stock_quantity" in data:
        cleaned["stock_quantity"] = normalize_stock_quantity(data.get("stock_quantity"))
    elif not partial:
        cleaned["stock_quantity"] = 0
    if "low_stock_alert" in data:
        cleaned["low_stock_alert"] = normalize_low_stock_alert(data.get("low_stock_alert"))
    elif not partial:
        cleaned["low_stock_alert"] = 1
    if "features" in data:
        cleaned["features"] = clean_text_list(data.get("features"), field="features")
    return cleaned


@router.get("/products")
def get_products(
    category: str = "all",
    search: str = "",
    page: int | None = Query(default=None, ge=1),
    per_page: int | None = Query(default=None, ge=1, le=60),
    db: Session = Depends(get_db),
):
    filters = [Product.is_active.is_(True)]
    if category and category != "all":
        filters.append(Product.category == category)
    search = search.strip()
    if search:
        search_pattern = f"%{search.lower()}%"
        filters.append(
            or_(
                func.lower(Product.name).like(search_pattern),
                func.lower(Product.description).like(search_pattern),
            )
        )

    statement = select(Product).where(*filters).order_by(Product.id)
    if page is None and per_page is None:
        products = db.scalars(statement).unique().all()
        return [product.to_dict() for product in products]

    current_page = page or 1
    page_size = per_page or 12
    total = db.scalar(select(func.count(Product.id)).where(*filters)) or 0
    products = db.scalars(
        statement.offset((current_page - 1) * page_size).limit(page_size)
    ).unique().all()
    total_pages = (total + page_size - 1) // page_size if total else 0
    return {
        "items": [product.to_dict() for product in products],
        "page": current_page,
        "per_page": page_size,
        "total": total,
        "total_pages": total_pages,
        "has_next": current_page < total_pages,
        "has_previous": current_page > 1 and total_pages > 0,
    }


@router.get("/admin/products")
def get_admin_products(
    _claims=Depends(admin_claims),
    db: Session = Depends(get_db),
):
    products = db.scalars(select(Product).order_by(Product.id)).unique().all()
    return [product.to_dict() for product in products]


@router.get("/admin/storage/status")
def get_storage_status(_claims=Depends(admin_claims)):
    return storage_status()


@router.get("/products/{product_id}")
def get_product(product_id: int, db: Session = Depends(get_db)):
    product = get_or_404(db, Product, product_id)
    if not product.is_active:
        raise HTTPException(status_code=404, detail="Produto nao encontrado")
    return product.to_dict()


@router.post("/products", status_code=201)
def create_product(
    data: dict[str, Any] = Body(default_factory=dict),
    _claims=Depends(admin_claims),
    db: Session = Depends(get_db),
):
    if any(not data.get(field) for field in ["name", "category", "price", "description"]):
        raise HTTPException(
            status_code=400,
            detail="Campos obrigatórios: name, category, price, description",
        )
    try:
        cleaned = normalize_product_payload(data)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    if cleaned.get("sku") and db.scalar(select(Product.id).where(Product.sku == cleaned["sku"])):
        raise HTTPException(status_code=409, detail="SKU ja cadastrado")
    product = Product(
        name=cleaned["name"],
        category=cleaned["category"],
        categoryName=cleaned.get("categoryName", cleaned["category"].capitalize()),
        price=cleaned["price"],
        oldPrice=cleaned.get("oldPrice"),
        sku=cleaned.get("sku"),
        icon=data.get("icon", "💎"),
        badge=cleaned.get("badge"),
        is_active=normalize_bool(data.get("is_active"), True),
        stock_status=normalize_stock_status(data.get("stock_status")),
        stock_quantity=cleaned["stock_quantity"],
        low_stock_alert=cleaned["low_stock_alert"],
        description=cleaned["description"],
        features=json.dumps(cleaned.get("features", []), ensure_ascii=False),
        custom=True,
    )
    product.icon = cleaned.get("icon") or product.icon
    sync_stock_status(product)
    db.add(product)
    db.flush()
    images = store_admin_gallery_images(product, product_image_list(data))
    replace_product_gallery(product, images)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(status_code=409, detail="SKU ja cadastrado") from exc
    return product.to_dict()


@router.put("/products/{product_id}")
def update_product(
    product_id: int,
    data: dict[str, Any] = Body(default_factory=dict),
    _claims=Depends(admin_claims),
    db: Session = Depends(get_db),
):
    product = get_or_404(db, Product, product_id)
    try:
        cleaned = normalize_product_payload(data, partial=True)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    if cleaned.get("sku") and db.scalar(
        select(Product.id).where(Product.sku == cleaned["sku"], Product.id != product_id)
    ):
        raise HTTPException(status_code=409, detail="SKU ja cadastrado")
    for field in ["name", "category", "categoryName", "icon", "badge", "description"]:
        if field in cleaned:
            setattr(product, field, cleaned[field])
    if "is_active" in data:
        product.is_active = normalize_bool(data["is_active"], True)
    if "stock_status" in data:
        product.stock_status = normalize_stock_status(data["stock_status"])
    if "sku" in data:
        product.sku = cleaned.get("sku")
    if "stock_quantity" in cleaned:
        product.stock_quantity = cleaned["stock_quantity"]
    if "low_stock_alert" in cleaned:
        product.low_stock_alert = cleaned["low_stock_alert"]
    if data.get("price") is not None:
        product.price = cleaned["price"]
    if "oldPrice" in data:
        product.oldPrice = cleaned.get("oldPrice")
    if "images" in data or "image" in data:
        images = store_admin_gallery_images(product, product_image_list(data))
        replace_product_gallery(product, images)
    if data.get("features") is not None:
        product.features = json.dumps(cleaned.get("features", []), ensure_ascii=False)
    sync_stock_status(product)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(status_code=409, detail="SKU ja cadastrado") from exc
    return product.to_dict()


@router.delete("/products/{product_id}")
def delete_product(
    product_id: int,
    _claims=Depends(admin_claims),
    db: Session = Depends(get_db),
):
    db.delete(get_or_404(db, Product, product_id))
    db.commit()
    return {"message": "Produto removido com sucesso"}


@router.delete("/admin/products")
def delete_all_products(
    request: Request,
    data: dict[str, Any] = Body(default_factory=dict),
    claims=Depends(admin_claims),
    db: Session = Depends(get_db),
):
    if data.get("confirm") != "LIMPAR CATALOGO":
        raise HTTPException(
            status_code=400,
            detail="Confirmacao invalida para limpar o catalogo",
        )
    products = db.scalars(select(Product)).unique().all()
    total = len(products)
    for product in products:
        db.delete(product)
    actor = db.get(User, int(claims["sub"])) if claims and claims.get("sub") else None
    record_admin_audit(
        db,
        request,
        "catalog.cleared",
        admin_user=actor,
        resource="catalog",
        metadata={"deleted": total},
    )
    db.commit()
    return {
        "message": "Catalogo limpo com sucesso",
        "deleted": total,
    }


@router.post("/products/import-folder")
def import_product_folder(
    request: Request,
    files: list[UploadFile] = File(...),
    claims=Depends(admin_claims),
    db: Session = Depends(get_db),
):
    normalized_files = []
    for uploaded in files:
        raw_name = (uploaded.filename or "").replace("\\", "/").strip("/")
        relative_path = PurePosixPath(raw_name)
        if not raw_name or relative_path.is_absolute() or ".." in relative_path.parts:
            raise HTTPException(
                status_code=400,
                detail=f"Caminho de arquivo inválido: {raw_name}",
            )
        normalized_files.append((uploaded, relative_path))

    manifests = [path for _, path in normalized_files if path.name == "manifest.json"]
    if len(manifests) != 1:
        raise HTTPException(
            status_code=400,
            detail="A pasta deve conter exatamente um arquivo manifest.json",
        )
    catalog_prefix = manifests[0].parent
    IMPORT_UPLOAD_ROOT.mkdir(parents=True, exist_ok=True)
    temp_root = IMPORT_UPLOAD_ROOT / secrets.token_hex(12)
    temp_root.mkdir()
    try:
        total_bytes = 0
        for uploaded, relative_path in normalized_files:
            if catalog_prefix != PurePosixPath("."):
                try:
                    relative_path = relative_path.relative_to(catalog_prefix)
                except ValueError:
                    continue
            extension = relative_path.suffix.lower()
            if extension not in IMPORT_UPLOAD_ALLOWED_EXTENSIONS:
                raise HTTPException(
                    status_code=400,
                    detail=f"Tipo de arquivo nao suportado: {relative_path.name}",
                )
            destination = temp_root.joinpath(*relative_path.parts)
            destination.parent.mkdir(parents=True, exist_ok=True)
            file_size = 0
            with destination.open("wb") as output:
                while chunk := uploaded.file.read(1024 * 1024):
                    file_size += len(chunk)
                    total_bytes += len(chunk)
                    if file_size > IMPORT_UPLOAD_MAX_FILE_BYTES:
                        raise HTTPException(
                            status_code=400,
                            detail=f"Arquivo maior que 20 MB: {relative_path.name}",
                        )
                    if total_bytes > IMPORT_UPLOAD_MAX_TOTAL_BYTES:
                        raise HTTPException(
                            status_code=400,
                            detail="Importacao maior que 250 MB",
                        )
                    output.write(chunk)
        try:
            from backend.import_products import import_catalog

            summary = import_catalog(temp_root)
        except (
            FileNotFoundError,
            KeyError,
            RuntimeError,
            TypeError,
            ValueError,
            json.JSONDecodeError,
        ) as exc:
            raise HTTPException(status_code=400, detail=f"Catálogo inválido: {exc}") from exc
    finally:
        shutil.rmtree(temp_root, ignore_errors=True)
    actor = db.get(User, int(claims["sub"])) if claims and claims.get("sub") else None
    record_admin_audit(
        db,
        request,
        "catalog.imported",
        admin_user=actor,
        resource="catalog",
        metadata=summary,
    )
    db.commit()
    return {"message": "Catálogo importado com sucesso", **summary}


@router.get("/categories")
def get_categories(db: Session = Depends(get_db)):
    rows = db.execute(
        select(
            Product.category.label("id"),
            func.min(Product.categoryName).label("name"),
        )
        .where(Product.is_active.is_(True))
        .group_by(Product.category)
        .order_by(func.min(Product.categoryName), Product.category)
    ).all()
    return [{"id": "all", "name": "Todos", "icon": CATEGORY_ICONS["all"]}] + [
        {
            "id": row.id,
            "name": row.name or row.id.capitalize(),
            "icon": CATEGORY_ICONS.get(row.id, CATEGORY_ICONS["all"]),
        }
        for row in rows
        if row.id
    ]
