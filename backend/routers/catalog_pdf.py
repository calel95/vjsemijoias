import re
import secrets
import shutil
from pathlib import Path

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from starlette.background import BackgroundTask

from backend.auth import admin_claims
from backend.catalog_pdf import (
    CatalogOptions,
    CatalogProduct,
    generate_catalog_pdf,
    split_values,
    title_from_filename,
    value_at,
)
from backend.config import IMPORT_UPLOAD_ROOT
from backend.database import get_db
from backend.services.validation import clean_text, validate_image_bytes
from backend.store_config import effective_store_settings


router = APIRouter(prefix="/api/admin")


@router.post(
    "/catalog-pdf",
    tags=["Admin - Catalogo PDF"],
    summary="Gerar catalogo PDF a partir de imagens",
    description=(
        "Envie as imagens na ordem desejada. Os campos nomes, precos, categorias "
        "e descricoes sao opcionais e aceitam valores separados por | ou por nova linha."
    ),
    responses={
        200: {
            "description": "Catalogo PDF pronto para download",
            "content": {"application/pdf": {}},
        }
    },
)
def generate_catalog_pdf_endpoint(
    images: list[UploadFile] = File(
        ...,
        description="Imagens dos produtos, na ordem em que aparecerao no catalogo.",
    ),
    names: str = Form(
        "",
        description="Nomes separados por |. Se vazio, o nome sera extraido do arquivo.",
    ),
    prices: str = Form("", description="Precos separados por |, na ordem das imagens."),
    categories: str = Form(
        "",
        description="Categorias separadas por |, na ordem das imagens.",
    ),
    descriptions: str = Form(
        "",
        description="Descricoes separadas por |, na ordem das imagens.",
    ),
    catalog_title: str = Form(""),
    collection: str = Form(""),
    slogan: str = Form(""),
    contact: str = Form(""),
    coupon: str = Form(""),
    products_per_page: int = Form(
        6,
        description="Use 4 para cards maiores ou 6 para o layout padrao 2x3.",
    ),
    output_filename: str = Form(""),
    _claims=Depends(admin_claims),
    db: Session = Depends(get_db),
):
    active_settings = effective_store_settings(db)
    if not images:
        raise HTTPException(status_code=400, detail="Adicione pelo menos uma imagem")
    if len(images) > 100:
        raise HTTPException(status_code=400, detail="Envie no maximo 100 imagens")
    if products_per_page not in {4, 6}:
        raise HTTPException(
            status_code=400,
            detail="products_per_page deve ser 4 ou 6",
        )

    work_root = IMPORT_UPLOAD_ROOT / "catalog-pdf" / secrets.token_hex(12)
    image_root = work_root / "images"
    image_root.mkdir(parents=True, exist_ok=True)
    name_values = split_values(names)
    price_values = split_values(prices)
    category_values = split_values(categories)
    description_values = split_values(descriptions)
    products = []
    try:
        for index, uploaded in enumerate(images):
            content = uploaded.file.read()
            try:
                _, extension = validate_image_bytes(
                    content,
                    uploaded.content_type or "",
                    filename=uploaded.filename or "",
                    max_bytes=20 * 1024 * 1024,
                )
            except ValueError as exc:
                raise HTTPException(
                    status_code=400,
                    detail=f"{uploaded.filename}: {exc}",
                ) from exc

            image_path = image_root / f"{index + 1:03d}{extension}"
            image_path.write_bytes(content)
            products.append(
                CatalogProduct(
                    title=clean_text(
                        value_at(
                            name_values,
                            index,
                            title_from_filename(uploaded.filename or ""),
                        ),
                        field="nome",
                        max_length=200,
                        required=True,
                    ),
                    image_path=image_path,
                    price=clean_text(value_at(price_values, index), field="preco", max_length=50),
                    category=clean_text(
                        value_at(category_values, index, "Semijoias"),
                        field="categoria",
                        max_length=50,
                    ),
                    description=clean_text(
                        value_at(description_values, index),
                        field="descricao",
                        max_length=500,
                    ),
                )
            )

        output_name = clean_text(
            output_filename,
            field="output_filename",
            max_length=120,
        ) or active_settings.catalog.filename
        safe_filename = re.sub(
            r"[^A-Za-z0-9._-]+",
            "-",
            Path(output_name).name,
        ).strip("-")
        if not safe_filename.lower().endswith(".pdf"):
            safe_filename += ".pdf"
        output_path = work_root / safe_filename
        result = generate_catalog_pdf(
            products,
            output_path,
            CatalogOptions(
                title=clean_text(catalog_title, field="catalog_title", max_length=120)
                or active_settings.catalog.title,
                collection=clean_text(collection, field="collection", max_length=120)
                or active_settings.catalog.collection,
                slogan=clean_text(slogan, field="slogan", max_length=120)
                or active_settings.brand.slogan,
                contact=clean_text(contact, field="contact", max_length=200)
                or active_settings.catalog_contact_line,
                coupon=clean_text(coupon, field="coupon", max_length=80)
                or active_settings.coupon_label,
                products_per_page=products_per_page,
            ),
        )
    except HTTPException:
        shutil.rmtree(work_root, ignore_errors=True)
        raise
    except Exception as exc:
        shutil.rmtree(work_root, ignore_errors=True)
        raise HTTPException(
            status_code=400,
            detail=f"Nao foi possivel gerar o catalogo: {exc}",
        ) from exc

    return FileResponse(
        output_path,
        media_type="application/pdf",
        filename=safe_filename,
        headers={
            "X-Catalog-Products": str(result["products"]),
            "X-Catalog-Pages": str(result["pages"]),
        },
        background=BackgroundTask(shutil.rmtree, work_root, ignore_errors=True),
    )
