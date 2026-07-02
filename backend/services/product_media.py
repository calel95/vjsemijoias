import logging
import re
import unicodedata

from fastapi import HTTPException

from backend.config import FRONTEND_ROOT
from backend.models import ProductImage
from backend.services.storage import r2_enabled, store_public_file
from backend.services.validation import decode_base64_image, validate_image_bytes


logger = logging.getLogger(__name__)


ADMIN_CATALOG_IMAGE_ROOT = FRONTEND_ROOT / "images" / "catalog" / "admin"
ADMIN_IMAGE_MAX_BYTES = 8 * 1024 * 1024
DATA_URL_IMAGE_RE = re.compile(
    r"^data:(image/[-+.a-z0-9]+);base64,(.+)$",
    re.IGNORECASE | re.DOTALL,
)
IMAGE_EXTENSIONS = {
    "image/jpeg": ".jpg",
    "image/jpg": ".jpg",
    "image/png": ".png",
    "image/webp": ".webp",
    "image/gif": ".gif",
}
STOCK_STATUSES = {"available", "out_of_stock", "preorder"}


def clean_image_path(value):
    path = str(value or "").strip()
    return path or None


def unique_image_paths(values):
    images = []
    seen = set()
    for value in values or []:
        image = clean_image_path(value)
        if not image or image in seen:
            continue
        images.append(image)
        seen.add(image)
    return images


def gallery_image_paths(product):
    gallery = getattr(product, "gallery_images", None) or []
    ordered = sorted(
        gallery,
        key=lambda item: (
            getattr(item, "position", 0) if getattr(item, "position", None) is not None else 0,
            getattr(item, "id", 0) if getattr(item, "id", None) is not None else 0,
        ),
    )
    return unique_image_paths(getattr(item, "path", None) for item in ordered)


def resolve_product_images(product):
    gallery_images = gallery_image_paths(product)
    if gallery_images:
        return gallery_images

    image = clean_image_path(getattr(product, "image", None))
    return [image] if image else []


def resolve_product_main_image(product):
    images = resolve_product_images(product)
    return images[0] if images else None


def serialize_product_media(product):
    image = resolve_product_main_image(product)
    images = resolve_product_images(product)
    return {
        "image": image,
        "imagem_url": image,
        "images": images,
    }


def product_image_list(data):
    images = data.get("images")
    if isinstance(images, list):
        return [image for image in (clean_image_path(item) for item in images) if image]
    image = clean_image_path(data.get("image"))
    return [image] if image else []


def normalize_stock_status(value):
    stock_status = str(value or "available").strip()
    if stock_status not in STOCK_STATUSES:
        raise HTTPException(status_code=400, detail="Status de estoque invalido")
    return stock_status


def storage_slug(value):
    normalized = unicodedata.normalize("NFKD", str(value or "produto"))
    ascii_value = normalized.encode("ascii", "ignore").decode("ascii")
    slug = "-".join(
        part
        for part in "".join(
            char.lower() if char.isalnum() else " " for char in ascii_value
        ).split()
        if part
    )
    return slug or "produto"


def save_admin_image(product, image_data, position):
    match = DATA_URL_IMAGE_RE.match(image_data)
    if not match:
        return image_data

    content_type = match.group(1).lower()
    extension = IMAGE_EXTENSIONS.get(content_type)
    if not extension:
        raise HTTPException(
            status_code=400,
            detail=f"Formato de imagem nao suportado: {content_type}",
        )

    try:
        content = decode_base64_image(match.group(2))
        content_type, extension = validate_image_bytes(
            content,
            content_type,
            max_bytes=ADMIN_IMAGE_MAX_BYTES,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    product_folder = f"{int(product.id):06d}-{storage_slug(product.name)}"
    if r2_enabled():
        key = f"catalog/admin/{product_folder}/img_{position + 1}{extension}"
        return store_public_file(key, content, content_type)

    destination_dir = ADMIN_CATALOG_IMAGE_ROOT / product_folder
    destination_dir.mkdir(parents=True, exist_ok=True)
    destination_path = destination_dir / f"img_{position + 1}{extension}"
    destination_path.write_bytes(content)
    return destination_path.relative_to(FRONTEND_ROOT).as_posix()


def generate_variants_for_local_product_image(image_path: str) -> dict:
    """Gera variantes thumbnail/card/detail para imagem local salva no upload.

    Regras:
    - Ignora URL externa, SVG, data URL, R2/URL absoluta.
    - Apenas gera para arquivos locais raster dentro de frontend/images.
    - Falha de variante nao quebra o fluxo principal.
    - Retorna relatorio simples com status e variantes geradas.
    """
    try:
        from backend.services.image_variants import generate_variants_for_image

        report = generate_variants_for_image(image_path, apply=True)
        if report.get("status") == "erro":
            logger.warning(
                "Variante nao gerada para %s: %s",
                image_path,
                report.get("reason", ""),
            )
        return {
            "image": image_path,
            "status": report.get("status", "erro"),
            "reason": report.get("reason", ""),
            "generated": report.get("generated", []),
        }
    except Exception as exc:
        logger.warning("Falha ao gerar variantes para %s: %s", image_path, exc)
        return {
            "image": image_path,
            "status": "erro",
            "reason": str(exc),
            "generated": [],
        }


def store_admin_gallery_images(product, images):
    saved = []
    for position, image in enumerate(images):
        path = save_admin_image(product, image, position)
        saved.append(path)
        if path and not path.startswith(("http://", "https://")) and not path.startswith("data:"):
            generate_variants_for_local_product_image(path)
    return saved


def replace_product_gallery(product, images):
    images = unique_image_paths(images)
    product.image = images[0] if images else None
    product.gallery_images.clear()
    for position, image in enumerate(images):
        product.gallery_images.append(ProductImage(path=image, position=position))
