import csv
from io import StringIO
from typing import Any

from fastapi import APIRouter, Body, Depends, HTTPException, Query, Request, Response
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from backend.auth import admin_claims
from backend.database import get_db
from backend.models import Product
from backend.routers.vj_admin_common import admin_user_id
from backend.services.admin_audit import record_vj_admin_audit
from backend.services.common import get_or_404
from backend.services.pricing import CALCULATED_PRICE_FIELDS, DEFAULT_MARKUP, DEFAULT_PACKAGING_COST
from backend.services.product_media import replace_product_gallery, store_admin_gallery_images
from backend.services.vj_products import (
    CSV_FIELDS,
    apply_product_fields,
    build_product,
    calculate_product_prices,
    deactivate_product as deactivate_vj_product,
    ensure_supplier_exists,
    product_csv_row,
    product_payload,
    products_statement,
    publish_product as publish_vj_product,
    unpublish_product as unpublish_vj_product,
)


router = APIRouter(prefix="/api/vj-admin", tags=["VJ Admin"])


def safe_storage_error(exc: RuntimeError) -> HTTPException:
    """Converte RuntimeError de storage em HTTPException segura sem expor secrets."""
    message = str(exc)
    if "R2" in message or "r2" in message.lower():
        detail = "Storage de imagens indisponivel: configuracao R2 incompleta. Verifique as variaveis obrigatorias."
    else:
        detail = "Storage de imagens indisponivel. Tente novamente ou contate o suporte."
    return HTTPException(status_code=503, detail=detail)


@router.get("/pricing/defaults")
def pricing_defaults(_claims=Depends(admin_claims)):
    from backend.services.pricing import PAYMENT_FEES

    return {
        "markup": float(DEFAULT_MARKUP),
        "custo_embalagem": float(DEFAULT_PACKAGING_COST),
        "taxas": {field: float(value) for field, value in PAYMENT_FEES.items()},
        "campos_calculados": list(CALCULATED_PRICE_FIELDS),
    }


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


@router.get("/produtos/{product_id}")
def get_admin_product(
    product_id: int,
    _claims=Depends(admin_claims),
    db: Session = Depends(get_db),
):
    return get_or_404(db, Product, product_id).to_dict()


@router.post("/produtos", status_code=201)
def create_product(
    request: Request,
    data: dict[str, Any] = Body(default_factory=dict),
    claims=Depends(admin_claims),
    db: Session = Depends(get_db),
):
    actor_id = admin_user_id(claims)
    try:
        cleaned = product_payload(data)
        ensure_supplier_exists(db, cleaned.get("fornecedor_id"))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    if db.scalar(select(Product.id).where(Product.codigo == cleaned["codigo"])):
        raise HTTPException(status_code=409, detail="Codigo ja cadastrado")
    product = build_product(cleaned, actor_id=actor_id)
    db.add(product)
    db.flush()
    if product.image:
        try:
            images = store_admin_gallery_images(product, [product.image])
            replace_product_gallery(product, images)
        except RuntimeError as exc:
            db.rollback()
            raise safe_storage_error(exc) from exc
    record_vj_admin_audit(
        db,
        request,
        admin_user_id=actor_id,
        action="produto_criado",
        resource="produto",
        resource_id=product.id,
        metadata={"codigo": product.codigo, "nome": product.name, "status": product.status},
    )
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(status_code=409, detail="Codigo ja cadastrado") from exc
    return product.to_dict()


@router.put("/produtos/{product_id}")
def update_product(
    product_id: int,
    request: Request,
    data: dict[str, Any] = Body(default_factory=dict),
    claims=Depends(admin_claims),
    db: Session = Depends(get_db),
):
    product = get_or_404(db, Product, product_id)
    actor_id = admin_user_id(claims)
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
    product.updated_by_id = actor_id
    if any(field in cleaned for field in ("custo_peca", "custo_embalagem", "markup")):
        calculate_product_prices(product, cleaned)
    if "image" in cleaned:
        try:
            images = store_admin_gallery_images(product, [product.image] if product.image else [])
            replace_product_gallery(product, images)
        except RuntimeError as exc:
            db.rollback()
            raise safe_storage_error(exc) from exc
    db.flush()
    record_vj_admin_audit(
        db,
        request,
        admin_user_id=actor_id,
        action="produto_atualizado",
        resource="produto",
        resource_id=product.id,
        metadata={"codigo": product.codigo, "nome": product.name, "campos": sorted(cleaned.keys())},
    )
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(status_code=409, detail="Codigo ja cadastrado") from exc
    return product.to_dict()


@router.post("/produtos/{product_id}/publicar")
def publish_product(
    product_id: int,
    request: Request,
    claims=Depends(admin_claims),
    db: Session = Depends(get_db),
):
    product = get_or_404(db, Product, product_id)
    actor_id = admin_user_id(claims)
    publish_vj_product(product, actor_id=actor_id)
    db.flush()
    record_vj_admin_audit(
        db,
        request,
        admin_user_id=actor_id,
        action="produto_publicado",
        resource="produto",
        resource_id=product.id,
        metadata={"codigo": product.codigo, "nome": product.name},
    )
    db.commit()
    return product.to_dict()


@router.post("/produtos/{product_id}/despublicar")
def unpublish_product(
    product_id: int,
    request: Request,
    claims=Depends(admin_claims),
    db: Session = Depends(get_db),
):
    product = get_or_404(db, Product, product_id)
    actor_id = admin_user_id(claims)
    unpublish_vj_product(product, actor_id=actor_id)
    db.flush()
    record_vj_admin_audit(
        db,
        request,
        admin_user_id=actor_id,
        action="produto_despublicado",
        resource="produto",
        resource_id=product.id,
        metadata={"codigo": product.codigo, "nome": product.name},
    )
    db.commit()
    return product.to_dict()


@router.post("/produtos/{product_id}/inativar")
def deactivate_product(
    product_id: int,
    request: Request,
    data: dict[str, Any] = Body(default_factory=dict),
    claims=Depends(admin_claims),
    db: Session = Depends(get_db),
):
    product = get_or_404(db, Product, product_id)
    actor_id = admin_user_id(claims)
    try:
        deactivate_vj_product(product, data.get("confirm"), actor_id=actor_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    db.flush()
    record_vj_admin_audit(
        db,
        request,
        admin_user_id=actor_id,
        action="produto_inativado",
        resource="produto",
        resource_id=product.id,
        metadata={"codigo": product.codigo, "nome": product.name},
    )
    db.commit()
    return product.to_dict()