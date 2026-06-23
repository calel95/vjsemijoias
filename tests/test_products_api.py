import shutil
from decimal import Decimal
from pathlib import Path

from backend.config import FRONTEND_ROOT
from backend.database import SessionLocal
from backend.models import Product
from backend.services.startup import seed_products
from tests.helpers import TINY_GIF_DATA_URL, admin_login, client


def test_admin_can_create_product_with_api_token():
    login = admin_login()
    token = login.json()['token']

    response = client.post(
        '/api/products',
        headers={'Authorization': f'Bearer {token}'},
        json={
            'name': 'Brinco Teste',
            'category': 'brincos',
            'categoryName': 'Brincos',
            'price': 89.9,
            'description': 'Produto criado pelo teste da API.',
            'features': ['Banho de ouro 18k'],
        },
    )

    assert response.status_code == 201
    product = response.json()
    assert product['name'] == 'Brinco Teste'
    assert product['price'] == 89.9
    assert product['stock_quantity'] == 0
    assert product['stock_status'] == 'out_of_stock'

    with SessionLocal() as db:
        stored = db.get(Product, product['id'])
        assert stored.price == Decimal('89.90')

def test_admin_can_manage_product_stock_fields():
    token = admin_login().json()['token']

    created = client.post(
        '/api/products',
        headers={'Authorization': f'Bearer {token}'},
        json={
            'name': 'Produto Estoque Teste',
            'category': 'brincos',
            'price': 59.9,
            'description': 'Produto com controle de estoque.',
            'sku': ' vj-estoque-001 ',
            'stock_quantity': 2,
            'low_stock_alert': 3,
        },
    )
    duplicate = client.post(
        '/api/products',
        headers={'Authorization': f'Bearer {token}'},
        json={
            'name': 'Produto SKU Duplicado',
            'category': 'brincos',
            'price': 49.9,
            'description': 'SKU duplicado.',
            'sku': 'VJ-ESTOQUE-001',
            'stock_quantity': 1,
        },
    )
    updated = client.put(
        f"/api/products/{created.json()['id']}",
        headers={'Authorization': f'Bearer {token}'},
        json={'stock_quantity': 0},
    )

    assert created.status_code == 201
    data = created.json()
    assert data['sku'] == 'VJ-ESTOQUE-001'
    assert data['stock_quantity'] == 2
    assert data['low_stock_alert'] == 3
    assert data['stock_is_low'] is True
    assert duplicate.status_code == 409
    assert updated.status_code == 200
    assert updated.json()['stock_status'] == 'out_of_stock'

def test_admin_product_input_is_sanitized_and_validated():
    token = admin_login().json()['token']

    invalid_price = client.post(
        '/api/products',
        headers={'Authorization': f'Bearer {token}'},
        json={
            'name': 'Produto Preco Ruim',
            'category': 'brincos',
            'price': -1,
            'description': 'Descricao',
        },
    )
    sanitized = client.post(
        '/api/products',
        headers={'Authorization': f'Bearer {token}'},
        json={
            'name': '<b>Produto Seguro</b>',
            'category': 'brincos',
            'categoryName': '<i>Brincos</i>',
            'price': 89.9,
            'description': '<script>alert(1)</script> Descricao segura',
            'features': ['<b>Banho 18k</b>'],
        },
    )

    assert invalid_price.status_code == 400
    assert sanitized.status_code == 201
    data = sanitized.json()
    assert data['name'] == 'Produto Seguro'
    assert data['categoryName'] == 'Brincos'
    assert '<' not in data['description']
    assert data['features'] == ['Banho 18k']

def test_admin_can_clear_catalog_only_with_explicit_confirmation():
    login = admin_login()
    token = login.json()['token']

    with SessionLocal() as db:
        before_count = db.query(Product).count()

    try:
        invalid = client.request(
            'DELETE',
            '/api/admin/products',
            headers={'Authorization': f'Bearer {token}'},
            json={'confirm': 'APAGAR'},
        )

        with SessionLocal() as db:
            unchanged_count = db.query(Product).count()

        deleted = client.request(
            'DELETE',
            '/api/admin/products',
            headers={'Authorization': f'Bearer {token}'},
            json={'confirm': 'LIMPAR CATALOGO'},
        )

        assert invalid.status_code == 400
        assert unchanged_count == before_count
        assert deleted.status_code == 200
        assert deleted.json()['deleted'] == before_count
        assert client.get('/api/products').json() == []
    finally:
        with SessionLocal() as db:
            seed_products(db)
            db.commit()

def test_inactive_product_is_hidden_from_public_catalog_but_visible_to_admin():
    login = admin_login()
    token = login.json()['token']

    created = client.post(
        '/api/products',
        headers={'Authorization': f'Bearer {token}'},
        json={
            'name': 'Produto Inativo Teste',
            'category': 'colares',
            'categoryName': 'Colares',
            'price': 129.9,
            'description': 'Produto oculto da vitrine.',
            'is_active': False,
            'stock_status': 'available',
        },
    )

    assert created.status_code == 201
    product = created.json()
    assert product['is_active'] is False

    public_products = client.get('/api/products').json()
    admin_products = client.get(
        '/api/admin/products',
        headers={'Authorization': f'Bearer {token}'},
    ).json()

    assert all(item['id'] != product['id'] for item in public_products)
    assert any(item['id'] == product['id'] for item in admin_products)
    assert client.get(f"/api/products/{product['id']}").status_code == 404

def test_admin_can_create_and_update_product_gallery():
    login = admin_login()
    token = login.json()['token']
    created_folder = None
    admin_image_root = FRONTEND_ROOT / 'images' / 'catalog' / 'admin'

    try:
        created = client.post(
            '/api/products',
            headers={'Authorization': f'Bearer {token}'},
            json={
                'name': 'Colar Galeria',
                'category': 'colares',
                'categoryName': 'Colares',
                'price': 199.9,
                'description': 'Produto com mais de uma foto.',
                'images': [TINY_GIF_DATA_URL, TINY_GIF_DATA_URL],
            },
        )

        assert created.status_code == 201
        product = created.json()
        created_folder = (FRONTEND_ROOT / Path(product['image'])).parent
        assert product['image'].startswith('images/catalog/admin/')
        assert product['image'].endswith('/img_1.gif')
        assert product['images'][0] == product['image']
        assert product['images'][1].endswith('/img_2.gif')
        assert not product['image'].startswith('data:image/')
        assert (FRONTEND_ROOT / Path(product['image'])).is_file()

        updated = client.put(
            f"/api/products/{product['id']}",
            headers={'Authorization': f'Bearer {token}'},
            json={
                'images': [product['image'], TINY_GIF_DATA_URL],
            },
        )

        assert updated.status_code == 200
        product = updated.json()
        assert product['image'].startswith('images/catalog/admin/')
        assert product['images'][0] == product['image']
        assert product['images'][1].endswith('/img_2.gif')
        assert all(not image.startswith('data:image/') for image in product['images'])
        assert (FRONTEND_ROOT / Path(product['images'][1])).is_file()
    finally:
        if created_folder and created_folder.is_relative_to(admin_image_root):
            shutil.rmtree(created_folder, ignore_errors=True)

def test_admin_product_gallery_rejects_mismatched_image_type():
    token = admin_login().json()['token']
    fake_png_with_gif_bytes = TINY_GIF_DATA_URL.replace('image/gif', 'image/png')

    response = client.post(
        '/api/products',
        headers={'Authorization': f'Bearer {token}'},
        json={
            'name': 'Produto Imagem Falsa',
            'category': 'brincos',
            'price': 89.9,
            'description': 'Imagem com mime divergente.',
            'images': [fake_png_with_gif_bytes],
        },
    )

    assert response.status_code == 400
    assert 'Tipo de imagem' in response.json()['error']
