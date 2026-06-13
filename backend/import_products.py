import argparse
import json
import shutil
import unicodedata
from collections import Counter, defaultdict
from decimal import Decimal, InvalidOperation
from pathlib import Path

from backend.app import Product, ProductImage, ProductImport, app, db


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SOURCE = PROJECT_ROOT / 'import_data' / 'catalogo_extraido'
CATALOG_IMAGE_ROOT = PROJECT_ROOT / 'images' / 'catalog'


def slugify(value):
    normalized = unicodedata.normalize('NFKD', value)
    ascii_value = normalized.encode('ascii', 'ignore').decode('ascii')
    return '-'.join(
        part for part in ''.join(
            char.lower() if char.isalnum() else ' '
            for char in ascii_value
        ).split()
        if part
    )


def parse_price(value):
    try:
        return float(Decimal(str(value).replace('.', '').replace(',', '.')))
    except (InvalidOperation, ValueError):
        raise ValueError(f'Preço inválido: {value!r}')


def category_for(title):
    title_upper = title.upper()
    if title_upper.startswith('PULSEIRA'):
        return 'pulseiras', 'Pulseiras', '⚜️'
    if title_upper.startswith('CHAVEIRO'):
        return 'chaveiros', 'Chaveiros', '🔑'
    if title_upper.startswith(('COLAR', 'MEDALHA', 'RELICÁRIO')):
        return 'colares', 'Colares', '📿'
    return 'pingentes', 'Pingentes', '💎'


def display_names(products):
    totals = Counter(item['title'] for item in products)
    indexes = defaultdict(int)
    result = {}
    for item in products:
        title = item['title']
        indexes[title] += 1
        formatted = title.title()
        if totals[title] > 1:
            formatted = f'{formatted} - Modelo {indexes[title]}'
        result[item['page']] = formatted
    return result


def copy_images(source_root, item, destination_slug, dry_run=False):
    destination_dir = CATALOG_IMAGE_ROOT / destination_slug
    image_paths = []

    for position, image in enumerate(item.get('images', []), start=1):
        source_path = source_root / image['file']
        if not source_path.is_file():
            raise FileNotFoundError(f'Imagem não encontrada: {source_path}')
        extension = source_path.suffix.lower() or '.jpeg'
        destination_path = destination_dir / f'img_{position}{extension}'
        if not dry_run:
            destination_dir.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source_path, destination_path)
        image_paths.append(destination_path.relative_to(PROJECT_ROOT).as_posix())

    return image_paths


def import_catalog(source=DEFAULT_SOURCE, dry_run=False):
    source = Path(source).resolve()
    manifest_path = source / 'manifest.json'
    manifest = json.loads(manifest_path.read_text(encoding='utf-8'))
    products = manifest.get('products') or []
    names = display_names(products)
    summary = {'created': 0, 'updated': 0, 'images': 0, 'products': len(products)}

    with app.app_context():
        for item in products:
            source_folder = item['folder']
            source_key = f"catalogo_extraido:page:{item['page']}:{source_folder}"
            import_record = ProductImport.query.filter_by(source_key=source_key).first()
            category, category_name, icon = category_for(item['title'])
            destination_slug = f"{int(item['page']):02d}-{slugify(item['title'])}"
            image_paths = copy_images(source, item, destination_slug, dry_run=dry_run)
            features = item.get('description_lines') or []
            description = '. '.join(line.rstrip('.') for line in features)
            if description:
                description += '.'
            else:
                description = names[item['page']]

            if import_record:
                product = import_record.product
                summary['updated'] += 1
            else:
                product = Product(custom=True)
                db.session.add(product)
                summary['created'] += 1

            product.name = names[item['page']]
            product.category = category
            product.categoryName = category_name
            product.price = parse_price(item['primary_price'])
            product.oldPrice = None
            product.image = image_paths[0] if image_paths else None
            product.icon = icon
            product.badge = 'new'
            product.description = description
            product.features = json.dumps(features, ensure_ascii=False)
            product.custom = True

            if not import_record:
                db.session.flush()
                import_record = ProductImport(
                    product_id=product.id,
                    source_key=source_key,
                    source_page=item.get('page'),
                    source_folder=source_folder,
                )
                db.session.add(import_record)

            product.gallery_images.clear()
            for position, path in enumerate(image_paths):
                product.gallery_images.append(ProductImage(path=path, position=position))
            summary['images'] += len(image_paths)

        if dry_run:
            db.session.rollback()
        else:
            db.session.commit()

    return summary


def main():
    parser = argparse.ArgumentParser(description='Importa o catálogo extraído para a loja.')
    parser.add_argument('source', nargs='?', default=DEFAULT_SOURCE)
    parser.add_argument('--dry-run', action='store_true')
    args = parser.parse_args()
    summary = import_catalog(args.source, dry_run=args.dry_run)
    mode = 'Simulação' if args.dry_run else 'Importação'
    print(
        f"{mode} concluída: {summary['products']} produtos, "
        f"{summary['created']} criados, {summary['updated']} atualizados, "
        f"{summary['images']} imagens."
    )


if __name__ == '__main__':
    main()
