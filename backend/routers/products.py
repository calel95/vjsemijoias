import json
import secrets
import shutil
from pathlib import PurePosixPath
from typing import Any

from fastapi import APIRouter, Body, Depends, File, HTTPException, UploadFile
from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.auth import admin_claims
from backend.config import IMPORT_UPLOAD_ROOT
from backend.database import get_db
from backend.models import Product
from backend.services.common import get_or_404, normalize_bool
from backend.services.product_media import (
    normalize_stock_status,
    product_image_list,
    replace_product_gallery,
    store_admin_gallery_images,
)


router = APIRouter(prefix="/api")


@router.get("/products")
def get_products(
    category: str = "all",
    search: str = "",
    db: Session = Depends(get_db),
):
    statement = select(Product).where(Product.is_active.is_(True)).order_by(Product.id)
    if category and category != "all":
        statement = statement.where(Product.category == category)
    products = db.scalars(statement).unique().all()
    search = search.lower()
    if search:
        products = [
            product
            for product in products
            if search in product.name.lower() or search in product.description.lower()
        ]
    return [product.to_dict() for product in products]


@router.get("/admin/products")
def get_admin_products(
    _claims=Depends(admin_claims),
    db: Session = Depends(get_db),
):
    products = db.scalars(select(Product).order_by(Product.id)).unique().all()
    return [product.to_dict() for product in products]


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
    product = Product(
        name=data["name"],
        category=data["category"],
        categoryName=data.get("categoryName", data["category"].capitalize()),
        price=float(data["price"]),
        oldPrice=float(data["oldPrice"]) if data.get("oldPrice") else None,
        icon=data.get("icon", "💎"),
        badge=data.get("badge"),
        is_active=normalize_bool(data.get("is_active"), True),
        stock_status=normalize_stock_status(data.get("stock_status")),
        description=data["description"],
        features=json.dumps(data.get("features", []), ensure_ascii=False),
        custom=True,
    )
    db.add(product)
    db.flush()
    images = store_admin_gallery_images(product, product_image_list(data))
    replace_product_gallery(product, images)
    db.commit()
    return product.to_dict()


@router.put("/products/{product_id}")
def update_product(
    product_id: int,
    data: dict[str, Any] = Body(default_factory=dict),
    _claims=Depends(admin_claims),
    db: Session = Depends(get_db),
):
    product = get_or_404(db, Product, product_id)
    for field in ["name", "category", "categoryName", "icon", "badge", "description"]:
        if data.get(field) is not None:
            setattr(product, field, data[field])
    if "is_active" in data:
        product.is_active = normalize_bool(data["is_active"], True)
    if "stock_status" in data:
        product.stock_status = normalize_stock_status(data["stock_status"])
    if data.get("price") is not None:
        product.price = float(data["price"])
    if "oldPrice" in data:
        product.oldPrice = float(data["oldPrice"]) if data["oldPrice"] else None
    if "images" in data or "image" in data:
        images = store_admin_gallery_images(product, product_image_list(data))
        replace_product_gallery(product, images)
    if data.get("features") is not None:
        product.features = json.dumps(data["features"], ensure_ascii=False)
    db.commit()
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


@router.post("/products/import-folder")
def import_product_folder(
    files: list[UploadFile] = File(...),
    _claims=Depends(admin_claims),
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
        for uploaded, relative_path in normalized_files:
            if catalog_prefix != PurePosixPath("."):
                try:
                    relative_path = relative_path.relative_to(catalog_prefix)
                except ValueError:
                    continue
            destination = temp_root.joinpath(*relative_path.parts)
            destination.parent.mkdir(parents=True, exist_ok=True)
            with destination.open("wb") as output:
                shutil.copyfileobj(uploaded.file, output)
        try:
            from backend.import_products import import_catalog

            summary = import_catalog(temp_root)
        except (FileNotFoundError, KeyError, TypeError, ValueError, json.JSONDecodeError) as exc:
            raise HTTPException(status_code=400, detail=f"Catálogo inválido: {exc}") from exc
    finally:
        shutil.rmtree(temp_root, ignore_errors=True)
    return {"message": "Catálogo importado com sucesso", **summary}


@router.get("/categories")
def get_categories():
    return [
        {"id": "all", "name": "Todos", "icon": "💎"},
        {"id": "brincos", "name": "Brincos", "icon": "✨"},
        {"id": "colares", "name": "Colares", "icon": "📿"},
        {"id": "pulseiras", "name": "Pulseiras", "icon": "⚜️"},
        {"id": "aneis", "name": "Anéis", "icon": "💍"},
        {"id": "pingentes", "name": "Pingentes", "icon": "🔮"},
        {"id": "chaveiros", "name": "Chaveiros", "icon": "🔑"},
        {"id": "conjuntos", "name": "Conjuntos", "icon": "🎁"},
    ]
