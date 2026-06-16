import argparse
import json
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SOURCE = PROJECT_ROOT / "import_data" / "catalogo_manual"
IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp"}


def title_from_folder(folder_name):
    return folder_name.replace("-", " ").replace("_", " ").title()


def build_manifest(source=DEFAULT_SOURCE):
    source = Path(source).resolve()
    products_root = source / "products"
    products = []

    if not products_root.exists():
        return {"products": products}

    for folder in sorted(path for path in products_root.iterdir() if path.is_dir()):
        images = [
            image.relative_to(source).as_posix()
            for image in sorted(folder.iterdir())
            if image.is_file() and image.suffix.lower() in IMAGE_EXTENSIONS
        ]
        if not images:
            continue

        products.append(
            {
                "name": title_from_folder(folder.name),
                "category": "",
                "price": "",
                "description": "",
                "features": [],
                "folder": folder.relative_to(source).as_posix(),
                "images": images,
            }
        )

    return {"products": products}


def main():
    parser = argparse.ArgumentParser(
        description="Gera um manifest inicial a partir das pastas de produtos."
    )
    parser.add_argument("source", nargs="?", default=DEFAULT_SOURCE)
    parser.add_argument(
        "--force",
        action="store_true",
        help="Sobrescreve manifest.json se ele ja existir.",
    )
    args = parser.parse_args()

    source = Path(args.source).resolve()
    source.mkdir(parents=True, exist_ok=True)
    manifest_path = source / "manifest.json"

    if manifest_path.exists() and not args.force:
        raise SystemExit(
            f"{manifest_path} ja existe. Use --force para sobrescrever."
        )

    manifest = build_manifest(source)
    manifest_path.write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    print(f"Manifest criado: {manifest_path}")
    print(f"Produtos encontrados: {len(manifest['products'])}")


if __name__ == "__main__":
    main()
