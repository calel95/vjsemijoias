import os
import json
from io import BytesIO

from werkzeug.datastructures import MultiDict

os.environ['DATABASE_URL'] = 'sqlite://'
os.environ['ADMIN_PASSWORD'] = 'test-admin-password'
os.environ['JWT_SECRET_KEY'] = 'test-jwt-secret-with-at-least-32-bytes'
os.environ['SECRET_KEY'] = 'test-secret'
os.environ['INFINITEPAY_HANDLE'] = 'vjsemijoias'
os.environ['PUBLIC_BASE_URL'] = 'https://vj.example.com'

from backend.app import app
from backend.import_products import DEFAULT_SOURCE, import_catalog


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
    client = app.test_client()
    response = client.get('/api/health')

    assert response.status_code == 200
    assert response.get_json()['status'] == 'ok'


def test_catalog_has_seed_products():
    client = app.test_client()
    response = client.get('/api/products')

    assert response.status_code == 200
    assert len(response.get_json()) == 10


def test_order_total_is_calculated_by_server():
    client = app.test_client()
    response = client.post('/api/orders', json={
        'customer_name': 'Cliente Teste',
        'customer_email': 'cliente@example.com',
        'customer_cpf': '12345678909',
        'items': [{'id': 1, 'quantity': 2, 'price': 0.01}],
        'total': 0.01,
        'coupon': 'VJ10',
    })

    assert response.status_code == 201
    order = response.get_json()
    assert order['subtotal'] == 299.8
    assert order['shipping'] == 0.0
    assert order['discount'] == 29.98
    assert order['total'] == 269.82
    assert order['status'] == 'pending'


def test_admin_route_requires_token():
    client = app.test_client()
    response = client.post('/api/products', json={})

    assert response.status_code == 401


def test_admin_can_create_product_with_api_token():
    client = app.test_client()
    login = client.post('/api/auth/admin/login', json={'password': 'test-admin-password'})
    token = login.get_json()['token']

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
    assert response.get_json()['name'] == 'Brinco Teste'


def test_admin_can_import_complete_catalog_folder():
    client = app.test_client()
    login = client.post('/api/auth/admin/login', json={'password': 'test-admin-password'})
    token = login.get_json()['token']
    upload = MultiDict()

    for path in DEFAULT_SOURCE.rglob('*'):
        if path.is_file():
            relative = path.relative_to(DEFAULT_SOURCE).as_posix()
            upload.add(
                'files',
                (BytesIO(path.read_bytes()), f'catalogo_extraido/{relative}'),
            )

    response = client.post(
        '/api/products/import-folder',
        headers={'Authorization': f'Bearer {token}'},
        data=upload,
        content_type='multipart/form-data',
    )

    assert response.status_code == 200
    data = response.get_json()
    expected_products, expected_images = catalog_totals()
    assert data['products'] == expected_products
    assert data['images'] == expected_images
    assert data['created'] == expected_products


def test_payment_config_exposes_infinitepay():
    client = app.test_client()
    response = client.get('/api/payments/config')

    assert response.status_code == 200
    assert response.get_json() == {
        'provider': 'infinitepay',
        'enabled': True,
        'max_installments': 12,
    }


def test_create_infinitepay_checkout_returns_redirect(monkeypatch):
    def fake_request(self, method, url, **kwargs):
        assert self.trust_env is False
        assert method == 'POST'
        assert url.endswith('/links')
        assert kwargs['json']['handle'] == 'vjsemijoias'
        assert kwargs['json']['items'][0]['price'] == 16980
        assert kwargs['json']['redirect_url'] == 'https://vj.example.com/checkout.html'
        assert kwargs['json']['webhook_url'] == (
            'https://vj.example.com/api/payments/webhook/infinitepay'
        )
        return FakeResponse({
            'url': 'https://checkout.infinitepay.com.br/teste',
        })

    monkeypatch.setattr('backend.infinitepay_client.requests.Session.request', fake_request)
    response = app.test_client().post(
        '/api/payments/infinitepay/checkout',
        json=order_payload(),
    )

    assert response.status_code == 201
    data = response.get_json()
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
            'amount': 16980,
            'paid_amount': 16980,
            'installments': 12,
            'capture_method': 'credit_card',
        })

    monkeypatch.setattr('backend.infinitepay_client.requests.Session.request', fake_request)
    client = app.test_client()
    created = client.post(
        '/api/payments/infinitepay/checkout',
        json=order_payload(),
    ).get_json()
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
    data = response.get_json()
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
            'amount': 16980,
            'paid_amount': 16980,
            'installments': 1,
            'capture_method': 'pix',
        })

    monkeypatch.setattr('backend.infinitepay_client.requests.Session.request', fake_request)
    client = app.test_client()
    created = client.post(
        '/api/payments/infinitepay/checkout',
        json=order_payload(),
    ).get_json()

    response = client.post('/api/payments/webhook/infinitepay', json={
        'invoice_slug': 'invoice-webhook',
        'amount': 16980,
        'paid_amount': 16980,
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
    ).get_json()
    assert payment['status'] == 'paid'
    assert payment['method'] == 'pix'


def test_catalog_import_dry_run_is_complete():
    summary = import_catalog(DEFAULT_SOURCE, dry_run=True)
    expected_products, expected_images = catalog_totals()

    assert summary['products'] == expected_products
    assert summary['images'] == expected_images
