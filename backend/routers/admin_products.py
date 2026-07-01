import json

from fastapi import APIRouter, Body, Depends, HTTPException, Request
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from backend.auth import admin_claims
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
from backend.services.product_payload import normalize_product_payload
from backend.services.stock import sync_stock_status
from backend.services.storage import storage_status


router = APIRouter(prefix="/api")


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


@router.post("/products", status_code=201)
def create_product(
    data: dict = Body(default_factory=dict),
    _claims=Depends(admin_claims),
    db: Session = Depends(get_db),
):
    if any(not data.get(field) for field in ["name", "category", "price", "description"]):
        raise HTTPException(
            status_code=400,
            detail="Campos obrigatÃ³rios: name, category, price, description",
        )
    try:
        cleaned = normalize_product_payload(data)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    if cleaned.get("sku") and db.scalar(select(Product.id).where(Product.sku == cleaned["sku"])):
        raise HTTPException(status_code=409, detail="SKU ja cadastrado")
    is_active = normalize_bool(data.get("is_active"), True)
    product = Product(
        name=cleaned["name"],
        category=cleaned["category"],
        categoryName=cleaned.get("categoryName", cleaned["category"].capitalize()),
        price=cleaned["price"],
        oldPrice=cleaned.get("oldPrice"),
        codigo=cleaned.get("sku"),
        sku=cleaned.get("sku"),
        reference=cleaned.get("reference"),
        icon=data.get("icon", "ðŸ’Ž"),
        badge=cleaned.get("badge"),
        status="publicado" if is_active else "rascunho",
        publicado=is_active,
        is_active=is_active,
        stock_status=normalize_stock_status(data.get("stock_status")),
        stock_quantity=cleaned["stock_quantity"],
        low_stock_alert=cleaned["low_stock_alert"],
        weight_grams=cleaned["weight_grams"],
        height_cm=cleaned["height_cm"],
        width_cm=cleaned["width_cm"],
        length_cm=cleaned["length_cm"],
        shipping_profile=cleaned["shipping_profile"],
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
    data: dict = Body(default_factory=dict),
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
        product.publicado = product.is_active
        product.status = "publicado" if product.is_active else "rascunho"
    if "stock_status" in data:
        product.stock_status = normalize_stock_status(data["stock_status"])
    if "sku" in data:
        product.sku = cleaned.get("sku")
        product.codigo = cleaned.get("sku") or product.codigo
    if "reference" in data:
        product.reference = cleaned.get("reference")
    if "stock_quantity" in cleaned:
        product.stock_quantity = cleaned["stock_quantity"]
    if "low_stock_alert" in cleaned:
        product.low_stock_alert = cleaned["low_stock_alert"]
    for field in ["weight_grams", "height_cm", "width_cm", "length_cm", "shipping_profile"]:
        if field in cleaned:
            setattr(product, field, cleaned[field])
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
    data: dict = Body(default_factory=dict),
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