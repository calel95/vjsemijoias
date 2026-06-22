import argparse
import json
import os
import shutil
import unicodedata
from collections import Counter, defaultdict
from decimal import Decimal, InvalidOperation
from pathlib import Path

from sqlalchemy import select

from backend.database import SessionLocal
from backend.models import Product, ProductImage, ProductImport
from backend.services.storage import r2_enabled, store_public_file
from backend.services.validation import clean_text, clean_text_list, validate_image_bytes


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SOURCE = PROJECT_ROOT / "import_data" / "catalogo_extraido"
FRONTEND_ROOT = PROJECT_ROOT / "frontend"
CATALOG_IMAGE_ROOT = FRONTEND_ROOT / "images" / "catalog"
IMPORT_IMAGE_MAX_BYTES = 20 * 1024 * 1024
IMPORT_CONTENT_TYPES = {
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".png": "image/png",
    ".webp": "image/webp",
    ".gif": "image/gif",
}

CATEGORY_MAP = {
    "aneis": ("aneis", "Aneis", "\U0001f48d"),
    "anel": ("aneis", "Aneis", "\U0001f48d"),
    "brincos": ("brincos", "Brincos", "\U0001f48e"),
    "brinco": ("brincos", "Brincos", "\U0001f48e"),
    "chaveiros": ("chaveiros", "Chaveiros", "\U0001f511"),
    "chaveiro": ("chaveiros", "Chaveiros", "\U0001f511"),
    "colares": ("colares", "Colares", "\U0001f4ff"),
    "colar": ("colares", "Colares", "\U0001f4ff"),
    "conjuntos": ("conjuntos", "Conjuntos", "\U0001f48e"),
    "conjunto": ("conjuntos", "Conjuntos", "\U0001f48e"),
    "pingentes": ("pingentes", "Pingentes", "\U0001f48e"),
    "pingente": ("pingentes", "Pingentes", "\U0001f48e"),
    "pulseiras": ("pulseiras", "Pulseiras", "\u269c\ufe0f"),
    "pulseira": ("pulseiras", "Pulseiras", "\u269c\ufe0f"),
}


def slugify(value):
    normalized = unicodedata.normalize("NFKD", str(value))
    ascii_value = normalized.encode("ascii", "ignore").decode("ascii")
    return "-".join(
        part
        for part in "".join(
            char.lower() if char.isalnum() else " " for char in ascii_value
        ).split()
        if part
    )


def parse_price(value):
    if isinstance(value, (int, float, Decimal)):
        return float(value)

    text = str(value).strip()
    if not text:
        raise ValueError("Preco vazio no manifest.")

    text = (
        text.replace("R$", "")
        .replace("r$", "")
        .replace("\xa0", "")
        .replace(" ", "")
    )
    if "," in text:
        text = text.replace(".", "").replace(",", ".")

    try:
        return float(Decimal(text))
    except (InvalidOperation, ValueError):
        raise ValueError(f"Preco invalido: {value!r}") from None


def category_for(title):
    title_slug = slugify(title)
    if title_slug.startswith("pulseira"):
        return CATEGORY_MAP["pulseiras"]
    if title_slug.startswith("chaveiro"):
        return CATEGORY_MAP["chaveiros"]
    if title_slug.startswith(("colar", "medalha", "relicario", "corrente")):
        return CATEGORY_MAP["colares"]
    if title_slug.startswith(("brinco", "argola")):
        return CATEGORY_MAP["brincos"]
    if title_slug.startswith("anel"):
        return CATEGORY_MAP["aneis"]
    if title_slug.startswith("conjunto"):
        return CATEGORY_MAP["conjuntos"]
    return CATEGORY_MAP["pingentes"]


def category_from_item(item, title):
    raw_category = str(
        item.get("category") or item.get("category_id") or item.get("categoria") or ""
    ).strip()
    if raw_category:
        category_id, category_name, icon = CATEGORY_MAP.get(
            slugify(raw_category),
            (slugify(raw_category), raw_category.title(), "\U0001f48e"),
        )
        return (
            item.get("category_id") or category_id,
            item.get("categoryName") or item.get("category_name") or category_name,
            item.get("icon") or icon,
        )
    return category_for(title)


def product_title(item):
    return str(item.get("name") or item.get("title") or item.get("nome") or "").strip()


def product_price(item):
    for key in ("price", "primary_price", "preco"):
        if key in item and str(item[key]).strip():
            return item[key]
    raise ValueError(f"Produto sem preco no manifest: {product_title(item)!r}")


def product_old_price(item):
    for key in ("oldPrice", "old_price", "preco_antigo"):
        if key in item and str(item[key]).strip():
            return parse_price(item[key])
    return None


def product_features(item):
    raw_features = item.get("features")
    if raw_features is None:
        raw_features = item.get("description_lines") or item.get("detalhes")

    if isinstance(raw_features, str):
        return [line.strip() for line in raw_features.splitlines() if line.strip()]
    if isinstance(raw_features, list):
        return [str(line).strip() for line in raw_features if str(line).strip()]
    return []


def product_description(item, title, features):
    description = str(item.get("description") or item.get("descricao") or "").strip()
    if description:
        return description
    if features:
        joined = ". ".join(line.rstrip(".") for line in features)
        return f"{joined}."
    return title


def product_folder(item, title, index):
    folder = str(item.get("folder") or item.get("source_folder") or "").strip()
    if folder:
        return folder.replace("\\", "/").strip("/")
    return f"products/{index:02d}-{slugify(title)}"


def product_source_key(item, source_folder, title):
    if item.get("source_key"):
        return str(item["source_key"])
    if item.get("page") is not None:
        return f"catalogo_extraido:page:{item['page']}:{source_folder}"
    return f"catalogo_manual:folder:{source_folder or slugify(title)}"


def product_destination_slug(item, title, index):
    if item.get("page") is not None:
        return f"{int(item['page']):02d}-{slugify(title)}"
    source_slug = slugify(item.get("folder") or title)
    return f"{index:02d}-{source_slug}"


def legacy_display_names(products):
    titles = [product_title(item) for item in products]
    totals = Counter(titles)
    indexes = defaultdict(int)
    result = {}
    for item, title in zip(products, titles, strict=False):
        if not item.get("page"):
            continue
        indexes[title] += 1
        formatted = title.title()
        if totals[title] > 1:
            formatted = f"{formatted} - Modelo {indexes[title]}"
        result[item["page"]] = formatted
    return result


def normalize_image_entry(image):
    if isinstance(image, str):
        return image.replace("\\", "/").strip("/")
    if isinstance(image, dict) and image.get("file"):
        return str(image["file"]).replace("\\", "/").strip("/")
    raise ValueError(f"Imagem invalida no manifest: {image!r}")


def copy_images(source_root, item, destination_slug, source_folder="", dry_run=False):
    destination_dir = CATALOG_IMAGE_ROOT / destination_slug
    image_paths = []

    for position, image in enumerate(item.get("images") or [], start=1):
        image_file = normalize_image_entry(image)
        source_path = source_root / image_file
        if not source_path.is_file() and source_folder:
            source_path = source_root / source_folder / image_file
        if not source_path.is_file():
            raise FileNotFoundError(f"Imagem nao encontrada: {source_path}")

        extension = source_path.suffix.lower() or ".jpeg"
        content_type = IMPORT_CONTENT_TYPES.get(extension)
        if not content_type:
            raise ValueError(f"Formato de imagem nao suportado: {source_path.name}")
        content = source_path.read_bytes()
        content_type, extension = validate_image_bytes(
            content,
            content_type,
            filename=source_path.name,
            max_bytes=IMPORT_IMAGE_MAX_BYTES,
        )
        destination_path = destination_dir / f"img_{position}{extension}"
        if not dry_run:
            if r2_enabled():
                key = f"catalog/imported/{destination_slug}/img_{position}{extension}"
                image_paths.append(store_public_file(key, content, content_type))
                continue
            destination_dir.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source_path, destination_path)
        image_paths.append(destination_path.relative_to(FRONTEND_ROOT).as_posix())

    return image_paths


def ensure_import_storage_is_safe(dry_run=False):
    if dry_run or r2_enabled():
        return
    app_env = os.getenv("APP_ENV", "").strip().lower()
    if app_env in {"development", "staging", "production"}:
        raise RuntimeError(
            "STORAGE_BACKEND=local nao deve ser usado para importar catalogo "
            "em ambiente remoto. Configure STORAGE_BACKEND=r2 e reimporte."
        )


def import_catalog(source=DEFAULT_SOURCE, dry_run=False):
    ensure_import_storage_is_safe(dry_run=dry_run)
    source = Path(source).resolve()
    manifest_path = source / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    products = manifest.get("products") or []
    legacy_names = legacy_display_names(products)
    summary = {"created": 0, "updated": 0, "images": 0, "products": len(products)}

    with SessionLocal() as db:
        for index, item in enumerate(products, start=1):
            title = product_title(item)
            if not title:
                raise ValueError(f"Produto #{index} sem name/title no manifest.")

            source_folder = product_folder(item, title, index)
            source_key = product_source_key(item, source_folder, title)
            import_record = db.scalar(
                select(ProductImport).where(ProductImport.source_key == source_key)
            )

            display_name = clean_text(
                item.get("display_name") or legacy_names.get(item.get("page")) or title,
                field="name",
                max_length=200,
                required=True,
            )
            category, category_name, icon = category_from_item(item, title)
            category = clean_text(category, field="category", max_length=50, required=True)
            category_name = clean_text(
                category_name,
                field="categoryName",
                max_length=50,
                required=True,
            )
            destination_slug = product_destination_slug(item, title, index)
            image_paths = copy_images(
                source,
                item,
                destination_slug,
                source_folder=source_folder,
                dry_run=dry_run,
            )
            features = clean_text_list(product_features(item), field="features")
            description = clean_text(
                product_description(item, display_name, features),
                field="description",
                max_length=1000,
                required=True,
            )

            if import_record:
                product = import_record.product
                summary["updated"] += 1
            else:
                product = Product(custom=True)
                db.add(product)
                summary["created"] += 1

            product.name = display_name
            product.category = category
            product.categoryName = category_name
            product.price = parse_price(product_price(item))
            product.oldPrice = product_old_price(item)
            product.image = image_paths[0] if image_paths else None
            product.icon = clean_text(item.get("icon") or icon, field="icon", max_length=10)
            product.badge = clean_text(item.get("badge", "new"), field="badge", max_length=20)
            product.description = description
            product.features = json.dumps(features, ensure_ascii=False)
            product.custom = bool(item.get("custom", True))

            if not import_record:
                db.flush()
                import_record = ProductImport(
                    product_id=product.id,
                    source_key=source_key,
                    source_page=item.get("page"),
                    source_folder=source_folder,
                )
                db.add(import_record)

            product.gallery_images.clear()
            for position, path in enumerate(image_paths):
                product.gallery_images.append(ProductImage(path=path, position=position))
            summary["images"] += len(image_paths)

        if dry_run:
            db.rollback()
        else:
            db.commit()

    return summary


def main():
    parser = argparse.ArgumentParser(description="Importa produtos para a loja.")
    parser.add_argument("source", nargs="?", default=DEFAULT_SOURCE)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    summary = import_catalog(args.source, dry_run=args.dry_run)
    mode = "Simulacao" if args.dry_run else "Importacao"
    print(
        f"{mode} concluida: {summary['products']} produtos, "
        f"{summary['created']} criados, {summary['updated']} atualizados, "
        f"{summary['images']} imagens."
    )


if __name__ == "__main__":
    main()
