import json
import shutil
from io import BytesIO
from pathlib import Path

import pytest
from pypdf import PdfReader

from backend.config import FRONTEND_ROOT
from backend.import_products import DEFAULT_SOURCE, import_catalog
from tests.helpers import admin_login, catalog_totals, client
from tools.generate_manual_manifest import build_manifest


def test_admin_can_import_complete_catalog_folder():
    login = admin_login()
    token = login.json()['token']
    upload = []

    for path in DEFAULT_SOURCE.rglob('*'):
        if path.is_file():
            relative = path.relative_to(DEFAULT_SOURCE).as_posix()
            upload.append(
                (
                    'files',
                    (
                        f'catalogo_extraido/{relative}',
                        path.read_bytes(),
                        'application/octet-stream',
                    ),
                )
            )

    response = client.post(
        '/api/products/import-folder',
        headers={'Authorization': f'Bearer {token}'},
        files=upload,
    )

    assert response.status_code == 200
    data = response.json()
    expected_products, expected_images = catalog_totals()
    assert data['products'] == expected_products
    assert data['images'] == expected_images
    assert data['created'] == expected_products

def test_admin_catalog_import_rejects_unsupported_file_type():
    token = admin_login().json()['token']
    response = client.post(
        '/api/products/import-folder',
        headers={'Authorization': f'Bearer {token}'},
        files=[
            ('files', ('catalogo/manifest.json', b'{"products":[]}', 'application/json')),
            ('files', ('catalogo/script.svg', b'<svg></svg>', 'image/svg+xml')),
        ],
    )

    assert response.status_code == 400
    assert 'Tipo de arquivo nao suportado' in response.json()['error']

def test_admin_can_generate_catalog_pdf():
    login = admin_login()
    token = login.json()['token']
    image = (
        DEFAULT_SOURCE
        / 'products'
        / '02_medalha_personalizada_iniciais_data'
        / 'img_1.jpeg'
    )

    response = client.post(
        '/api/admin/catalog-pdf',
        headers={'Authorization': f'Bearer {token}'},
        files=[
            ('images', ('medalha.jpeg', image.read_bytes(), 'image/jpeg')),
        ],
        data={
            'names': 'Medalha Personalizada',
            'prices': '199,00',
            'categories': 'Colares',
            'descriptions': 'Banho 18K e dois anos de garantia',
            'catalog_title': 'Catálogo de Teste',
            'products_per_page': '6',
        },
    )

    assert response.status_code == 200
    assert response.headers['content-type'] == 'application/pdf'
    assert response.headers['x-catalog-products'] == '1'
    assert response.headers['x-catalog-pages'] == '2'
    reader = PdfReader(BytesIO(response.content))
    assert len(reader.pages) == 2

def test_catalog_pdf_rejects_fake_image_upload():
    token = admin_login().json()['token']

    response = client.post(
        '/api/admin/catalog-pdf',
        headers={'Authorization': f'Bearer {token}'},
        files=[
            ('images', ('fake.png', b'nao-e-imagem', 'image/png')),
        ],
        data={'products_per_page': '6'},
    )

    assert response.status_code == 400
    assert 'imagem' in response.json()['error'].lower()

def test_catalog_import_dry_run_is_complete():
    summary = import_catalog(DEFAULT_SOURCE, dry_run=True)
    expected_products, expected_images = catalog_totals()

    assert summary['products'] == expected_products
    assert summary['images'] == expected_images

def test_remote_catalog_import_rejects_local_storage(monkeypatch):
    monkeypatch.setenv('APP_ENV', 'development')
    monkeypatch.setenv('STORAGE_BACKEND', 'local')

    with pytest.raises(RuntimeError, match='STORAGE_BACKEND=local'):
        import_catalog(DEFAULT_SOURCE)

def test_manual_catalog_manifest_import_and_generator():
    source = Path('.tmp/test-manual-catalog').resolve()
    shutil.rmtree(source, ignore_errors=True)
    try:
        product_folder = source / 'products' / 'colar-coracao-personalizado'
        product_folder.mkdir(parents=True)
        image = (
            DEFAULT_SOURCE
            / 'products'
            / '02_medalha_personalizada_iniciais_data'
            / 'img_1.jpeg'
        )
        shutil.copy2(image, product_folder / 'img_1.jpeg')

        manifest = build_manifest(source)
        manifest['products'][0].update({
            'name': 'Colar Coracao Personalizado',
            'category': 'colares',
            'price': '139,00',
            'description': 'Colar personalizado com banho 18K.',
            'features': ['Banho 18K', 'Garantia de 2 anos'],
        })
        (source / 'manifest.json').write_text(
            json.dumps(manifest, ensure_ascii=False),
            encoding='utf-8',
        )

        summary = import_catalog(source, dry_run=True)

        assert manifest['products'][0]['folder'] == 'products/colar-coracao-personalizado'
        assert manifest['products'][0]['images'] == [
            'products/colar-coracao-personalizado/img_1.jpeg',
        ]
        assert summary['products'] == 1
        assert summary['images'] == 1
        assert summary['created'] == 1
    finally:
        shutil.rmtree(source, ignore_errors=True)
