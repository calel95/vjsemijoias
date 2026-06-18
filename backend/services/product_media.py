import base64
import binascii
import re
import unicodedata

from fastapi import HTTPException

from backend.config import FRONTEND_ROOT
from backend.models import ProductImage
from backend.services.storage import r2_enabled, store_public_file


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


def product_image_list(data):
    images = data.get("images")
    if isinstance(images, list):
        return [str(image).strip() for image in images if str(image).strip()]
    image = data.get("image")
    return [str(image).strip()] if image else []


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
        content = base64.b64decode(match.group(2), validate=True)
    except (binascii.Error, ValueError) as exc:
        raise HTTPException(status_code=400, detail="Imagem enviada em base64 invalida") from exc

    if not content:
        raise HTTPException(status_code=400, detail="Imagem vazia")
    if len(content) > ADMIN_IMAGE_MAX_BYTES:
        raise HTTPException(status_code=400, detail="Imagem maior que 8 MB")

    product_folder = f"{int(product.id):06d}-{storage_slug(product.name)}"
    if r2_enabled():
        key = f"catalog/admin/{product_folder}/img_{position + 1}{extension}"
        return store_public_file(key, content, content_type)

    destination_dir = ADMIN_CATALOG_IMAGE_ROOT / product_folder
    destination_dir.mkdir(parents=True, exist_ok=True)
    destination_path = destination_dir / f"img_{position + 1}{extension}"
    destination_path.write_bytes(content)
    return destination_path.relative_to(FRONTEND_ROOT).as_posix()


def store_admin_gallery_images(product, images):
    return [save_admin_image(product, image, position) for position, image in enumerate(images)]


def replace_product_gallery(product, images):
    product.image = images[0] if images else None
    product.gallery_images.clear()
    for position, image in enumerate(images):
        product.gallery_images.append(ProductImage(path=image, position=position))
