import os
import json
import shutil
from io import BytesIO
from pathlib import Path

from fastapi.testclient import TestClient
from pypdf import PdfReader

os.environ['DATABASE_URL'] = 'sqlite://'
os.environ['ADMIN_PASSWORD'] = 'test-admin-password'
os.environ['JWT_SECRET_KEY'] = 'test-jwt-secret-with-at-least-32-bytes'
os.environ['SECRET_KEY'] = 'test-secret'
os.environ['INFINITEPAY_HANDLE'] = 'vjsemijoias'
os.environ['PUBLIC_BASE_URL'] = 'https://vj.example.com'

from backend.app import app
from backend.config import FRONTEND_ROOT, database_url
from backend.import_products import DEFAULT_SOURCE, import_catalog
from backend.store_config import store_settings
from tools.generate_manual_manifest import build_manifest


client = TestClient(app)
TINY_GIF_DATA_URL = 'data:image/gif;base64,R0lGODlhAQABAIAAAAAAAP///ywAAAAAAQABAAACAUwAOw=='


class FakeResponse:
    def __init__(self, data, status_code=200):
        self.data = data
        self.status_code = status_code
        self.ok = 200 <= status_code < 300
        self.text = ''

    def json(self):
        return self.data


def order_payload():
    return {
        'customer_name': 'Cliente Teste',
        'customer_email': 'cliente@example.com',
        'customer_cpf': '12345678909',
        'customer_phone': '11999999999',
        'address_zip': '01001000',
        'address_street': 'Praça da Sé',
        'address_number': '1',
        'address_neighborhood': 'Sé',
        'address_city': 'São Paulo',
        'address_state': 'SP',
        'items': [{'id': 1, 'quantity': 1}],
    }


def catalog_totals():
    manifest = json.loads(
        (DEFAULT_SOURCE / 'manifest.json').read_text(encoding='utf-8')
    )
    products = manifest.get('products') or []
    return len(products), sum(len(product.get('images') or []) for product in products)


def test_health():
    response = client.get('/api/health')

    assert response.status_code == 200
    assert response.json()['status'] == 'ok'


def test_database_url_uses_psycopg_for_postgresql(monkeypatch):
    monkeypatch.setenv(
        'DATABASE_URL',
        'postgresql://user:password@example.neon.tech/neondb?sslmode=require',
    )

    assert database_url() == (
        'postgresql+psycopg://user:password@example.neon.tech/neondb?sslmode=require'
    )


def test_frontend_files_are_served():
    index_response = client.get('/')
    css_response = client.get('/css/style.css')
    admin_response = client.get('/admin')
    legacy_catalog_response = client.get('/catalogo.html')
    manifest_response = client.get('/manifest.json')
    service_worker_response = client.get('/service-worker.js')

    assert index_response.status_code == 200
    assert b'VJ Semijoias' in index_response.content
    assert css_response.status_code == 200
    assert admin_response.status_code == 200
    assert b'<!DOCTYPE html>' in admin_response.content
    assert legacy_catalog_response.status_code == 200
    assert manifest_response.status_code == 200
    assert service_worker_response.status_code == 200


def test_catalog_has_seed_products():
    response = client.get('/api/products')

    assert response.status_code == 200
    assert len(response.json()) == 10


def test_order_total_is_calculated_by_server():
    response = client.post('/api/orders', json={
        'customer_name': 'Cliente Teste',
        'customer_email': 'cliente@example.com',
        'customer_cpf': '12345678909',
        'items': [{'id': 1, 'quantity': 2, 'price': 0.01}],
        'total': 0.01,
        'coupon': 'VJ10',
    })

    assert response.status_code == 201
    order = response.json()
    assert order['subtotal'] == 299.8
    assert order['shipping'] == 0.0
    assert order['discount'] == 29.98
    assert order['total'] == 269.82
    assert order['status'] == 'pending'


def test_shipping_is_free_below_old_threshold():
    order_response = client.post('/api/orders', json={
        'customer_name': 'Cliente Teste',
        'customer_email': 'cliente@example.com',
        'customer_cpf': '12345678909',
        'items': [{'id': 5, 'quantity': 1}],
    })
    shipping_response = client.post('/api/shipping/calculate', json={
        'total': 99.9,
        'zip_code': '01001000',
    })

    assert order_response.status_code == 201
    assert order_response.json()['shipping'] == 0.0
    assert order_response.json()['total'] == 99.9
    assert shipping_response.status_code == 200
    assert shipping_response.json()['shipping'] == 0


def test_store_config_exposes_shipping_and_coupon_settings():
    response = client.get('/api/store/config')

    assert response.status_code == 200
    data = response.json()
    assert data['brand']['name'] == 'VJ Semijoias'
    assert data['contact']['instagram'] == 'vj_semijoias'
    assert data['catalog']['filename'] == 'catalogo-vj-semijoias.pdf'
    assert data['shipping']['mode'] == 'free'
    assert data['coupon']['enabled'] is True
    assert data['coupon']['code'] == 'VJ10'


def test_fixed_shipping_can_be_configured_by_environment():
    original_mode = store_settings.shipping.mode
    original_value = store_settings.shipping.fixed_value
    try:
        object.__setattr__(store_settings.shipping, 'mode', 'fixed')
        object.__setattr__(store_settings.shipping, 'fixed_value', '19.90')

        response = client.post('/api/shipping/calculate', json={
            'total': 99.9,
            'zip_code': '01001000',
        })

        assert response.status_code == 200
        assert response.json()['shipping'] == 19.9
    finally:
        object.__setattr__(store_settings.shipping, 'mode', original_mode)
        object.__setattr__(store_settings.shipping, 'fixed_value', original_value)


def test_admin_can_update_order_status():
    login = client.post('/api/auth/admin/login', json={'password': 'test-admin-password'})
    token = login.json()['token']
    order_response = client.post('/api/orders', json={
        'customer_name': 'Cliente Status',
        'customer_email': 'status@example.com',
        'customer_cpf': '12345678909',
        'items': [{'id': 2, 'quantity': 1}],
    })
    order_id = order_response.json()['id']

    updated = client.put(
        f'/api/admin/orders/{order_id}/status',
        headers={'Authorization': f'Bearer {token}'},
        json={'status': 'processing'},
    )
    invalid = client.put(
        f'/api/admin/orders/{order_id}/status',
        headers={'Authorization': f'Bearer {token}'},
        json={'status': 'inventado'},
    )

    assert order_response.status_code == 201
    assert updated.status_code == 200
    assert updated.json()['status'] == 'processing'
    assert invalid.status_code == 400


def test_admin_route_requires_token():
    response = client.post('/api/products', json={})

    assert response.status_code == 401


def test_admin_can_create_product_with_api_token():
    login = client.post('/api/auth/admin/login', json={'password': 'test-admin-password'})
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
    assert response.json()['name'] == 'Brinco Teste'


def test_inactive_product_is_hidden_from_public_catalog_but_visible_to_admin():
    login = client.post('/api/auth/admin/login', json={'password': 'test-admin-password'})
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


def test_out_of_stock_product_cannot_be_ordered():
    login = client.post('/api/auth/admin/login', json={'password': 'test-admin-password'})
    token = login.json()['token']
    created = client.post(
        '/api/products',
        headers={'Authorization': f'Bearer {token}'},
        json={
            'name': 'Produto Sem Estoque Teste',
            'category': 'aneis',
            'categoryName': 'Aneis',
            'price': 99.9,
            'description': 'Produto indisponivel.',
            'stock_status': 'out_of_stock',
        },
    )
    product = created.json()

    response = client.post('/api/orders', json={
        'customer_name': 'Cliente Teste',
        'customer_email': 'cliente@example.com',
        'customer_cpf': '12345678909',
        'items': [{'id': product['id'], 'quantity': 1}],
    })

    assert created.status_code == 201
    assert response.status_code == 400
    assert 'dispon' in response.json()['error']


def test_admin_can_create_and_update_product_gallery():
    login = client.post('/api/auth/admin/login', json={'password': 'test-admin-password'})
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


def test_admin_can_import_complete_catalog_folder():
    login = client.post('/api/auth/admin/login', json={'password': 'test-admin-password'})
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


def test_admin_can_generate_catalog_pdf():
    login = client.post('/api/auth/admin/login', json={'password': 'test-admin-password'})
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


def test_payment_config_exposes_infinitepay():
    response = client.get('/api/payments/config')

    assert response.status_code == 200
    data = response.json()
    assert data['provider'] == 'infinitepay'
    assert data['enabled'] is True
    assert data['max_installments'] == 12
    assert data['store']['name'] == 'VJ Semijoias'
    assert data['store']['public_base_url'] == 'https://vj.example.com'


def test_create_infinitepay_checkout_returns_redirect(monkeypatch):
    def fake_request(self, method, url, **kwargs):
        assert self.trust_env is False
        assert method == 'POST'
        assert url.endswith('/links')
        assert kwargs['json']['handle'] == 'vjsemijoias'
        assert kwargs['json']['items'][0]['price'] == 14990
        assert kwargs['json']['redirect_url'] == 'https://vj.example.com/checkout'
        assert kwargs['json']['webhook_url'] == (
            'https://vj.example.com/api/payments/webhook/infinitepay'
        )
        return FakeResponse({
            'url': 'https://checkout.infinitepay.com.br/teste',
        })

    monkeypatch.setattr('backend.infinitepay_client.requests.Session.request', fake_request)
    response = client.post(
        '/api/payments/infinitepay/checkout',
        json=order_payload(),
    )

    assert response.status_code == 201
    data = response.json()
    assert data['payment']['status'] == 'pending'
    assert data['payment']['provider'] == 'infinitepay'
    assert data['checkout_url'] == 'https://checkout.infinitepay.com.br/teste'
    assert data['order']['status'] == 'pending'


def test_infinitepay_return_confirms_payment(monkeypatch):
    def fake_request(self, method, url, **kwargs):
        if url.endswith('/links'):
            return FakeResponse({
                'url': 'https://checkout.infinitepay.com.br/teste',
            })
        return FakeResponse({
            'success': True,
            'paid': True,
            'amount': 14990,
            'paid_amount': 14990,
            'installments': 12,
            'capture_method': 'credit_card',
        })

    monkeypatch.setattr('backend.infinitepay_client.requests.Session.request', fake_request)
    created = client.post(
        '/api/payments/infinitepay/checkout',
        json=order_payload(),
    ).json()
    local_order_id = created['order']['id']

    response = client.post(
        '/api/payments/infinitepay/confirm',
        json={
            'order_nsu': local_order_id,
            'transaction_nsu': 'transaction-123',
            'slug': 'invoice-123',
            'capture_method': 'credit_card',
        },
    )

    assert response.status_code == 200
    data = response.json()
    assert data['payment']['status'] == 'paid'
    assert data['payment']['method'] == 'credit_card'
    assert data['order']['status'] == 'paid'


def test_infinitepay_webhook_checks_provider_before_approval(monkeypatch):
    def fake_request(self, method, url, **kwargs):
        if url.endswith('/links'):
            return FakeResponse({'url': 'https://checkout.infinitepay.com.br/teste'})
        return FakeResponse({
            'success': True,
            'paid': True,
            'amount': 14990,
            'paid_amount': 14990,
            'installments': 1,
            'capture_method': 'pix',
        })

    monkeypatch.setattr('backend.infinitepay_client.requests.Session.request', fake_request)
    created = client.post(
        '/api/payments/infinitepay/checkout',
        json=order_payload(),
    ).json()

    response = client.post('/api/payments/webhook/infinitepay', json={
        'invoice_slug': 'invoice-webhook',
        'amount': 14990,
        'paid_amount': 14990,
        'installments': 1,
        'capture_method': 'pix',
        'transaction_nsu': 'transaction-webhook',
        'order_nsu': created['order']['id'],
        'items': [],
    })

    assert response.status_code == 200
    payment = client.get(
        f"/api/payments/{created['order']['id']}/status"
        f"?token={created['payment']['checkout_token']}"
    ).json()
    assert payment['status'] == 'paid'
    assert payment['method'] == 'pix'


def test_catalog_import_dry_run_is_complete():
    summary = import_catalog(DEFAULT_SOURCE, dry_run=True)
    expected_products, expected_images = catalog_totals()

    assert summary['products'] == expected_products
    assert summary['images'] == expected_images


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
