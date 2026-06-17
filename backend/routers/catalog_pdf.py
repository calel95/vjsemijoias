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
from backend.store_config import effective_store_settings


router = APIRouter(prefix="/api/admin")


@router.post(
    "/catalog-pdf",
    tags=["Admin - Catálogo PDF"],
    summary="Gerar catálogo PDF a partir de imagens",
    description=(
        "Envie as imagens na ordem desejada. Os campos nomes, preços, categorias "
        "e descrições são opcionais e aceitam valores separados por | ou por nova linha."
    ),
    responses={
        200: {
            "description": "Catálogo PDF pronto para download",
            "content": {"application/pdf": {}},
        }
    },
)
def generate_catalog_pdf_endpoint(
    images: list[UploadFile] = File(
        ...,
        description="Imagens dos produtos, na ordem em que aparecerão no catálogo.",
    ),
    names: str = Form(
        "",
        description="Nomes separados por |. Se vazio, o nome será extraído do arquivo.",
    ),
    prices: str = Form("", description="Preços separados por |, na ordem das imagens."),
    categories: str = Form(
        "",
        description="Categorias separadas por |, na ordem das imagens.",
    ),
    descriptions: str = Form(
        "",
        description="Descrições separadas por |, na ordem das imagens.",
    ),
    catalog_title: str = Form(""),
    collection: str = Form(""),
    slogan: str = Form(""),
    contact: str = Form(""),
    coupon: str = Form(""),
    products_per_page: int = Form(
        6,
        description="Use 4 para cards maiores ou 6 para o layout padrão 2x3.",
    ),
    output_filename: str = Form(""),
    _claims=Depends(admin_claims),
    db: Session = Depends(get_db),
):
    active_settings = effective_store_settings(db)
    if not images:
        raise HTTPException(status_code=400, detail="Adicione pelo menos uma imagem")
    if len(images) > 100:
        raise HTTPException(status_code=400, detail="Envie no máximo 100 imagens")
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
            if not (uploaded.content_type or "").startswith("image/"):
                raise HTTPException(
                    status_code=400,
                    detail=f"Arquivo não é uma imagem: {uploaded.filename}",
                )
            extension = Path(uploaded.filename or "").suffix.lower() or ".jpg"
            image_path = image_root / f"{index + 1:03d}{extension}"
            size = 0
            with image_path.open("wb") as output:
                while chunk := uploaded.file.read(1024 * 1024):
                    size += len(chunk)
                    if size > 20 * 1024 * 1024:
                        raise HTTPException(
                            status_code=400,
                            detail=f"Imagem maior que 20 MB: {uploaded.filename}",
                        )
                    output.write(chunk)
            products.append(
                CatalogProduct(
                    title=value_at(
                        name_values,
                        index,
                        title_from_filename(uploaded.filename or ""),
                    ),
                    image_path=image_path,
                    price=value_at(price_values, index),
                    category=value_at(category_values, index, "Semijoias"),
                    description=value_at(description_values, index),
                )
            )

        output_name = output_filename.strip() or active_settings.catalog.filename
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
                title=catalog_title.strip() or active_settings.catalog.title,
                collection=collection.strip() or active_settings.catalog.collection,
                slogan=slogan.strip() or active_settings.brand.slogan,
                contact=contact.strip() or active_settings.catalog_contact_line,
                coupon=coupon.strip() or active_settings.coupon_label,
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
            detail=f"Não foi possível gerar o catálogo: {exc}",
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
