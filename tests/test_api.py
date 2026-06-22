import json
import shutil
from uuid import uuid4
from io import BytesIO
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from pypdf import PdfReader

from backend.app import ADMIN_LOGIN_ATTEMPTS, app
from backend.config import FRONTEND_ROOT, database_url, settings
from backend.database import SessionLocal
from backend.import_products import DEFAULT_SOURCE, import_catalog
from backend.models import AdminAuditLog, Product, StoreSetting, User
from backend.services.rate_limit import clear_rate_limit_state
from backend.services.startup import seed_products, sync_default_coupon
from backend.store_config import store_settings
from tests.helpers import (
    ADMIN_EMAIL,
    TINY_GIF_DATA_URL,
    FakeResponse,
    admin_headers,
    admin_login,
    client,
)
from tools.generate_manual_manifest import build_manifest


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


def clear_store_setting_overrides():
    with SessionLocal() as db:
        db.query(StoreSetting).delete()
        sync_default_coupon(db)
        db.commit()


def test_health():
    response = client.get('/api/health')

    assert response.status_code == 200
    assert response.json()['status'] == 'ok'


def test_ready_checks_database():
    response = client.get('/api/ready')

    assert response.status_code == 200
    assert response.json() == {'status': 'ready', 'database': 'ok'}


def test_cors_allows_configured_origin_only():
    allowed = client.options(
        '/api/products',
        headers={
            'Origin': 'https://vj.example.com',
            'Access-Control-Request-Method': 'GET',
        },
    )
    blocked = client.options(
        '/api/products',
        headers={
            'Origin': 'https://malicioso.example',
            'Access-Control-Request-Method': 'GET',
        },
    )

    assert allowed.status_code == 200
    assert allowed.headers['access-control-allow-origin'] == 'https://vj.example.com'
    assert 'access-control-allow-origin' not in blocked.headers


def test_rate_limit_blocks_auth_requests_and_sets_headers():
    original_enabled = settings.rate_limit_enabled
    original_auth = settings.rate_limit_auth_per_minute
    original_global = settings.rate_limit_global_per_minute
    try:
        object.__setattr__(settings, 'rate_limit_enabled', True)
        object.__setattr__(settings, 'rate_limit_auth_per_minute', 2)
        object.__setattr__(settings, 'rate_limit_global_per_minute', 100)
        clear_rate_limit_state()

        headers = {'X-Forwarded-For': '203.0.113.10'}
        first = client.post('/api/auth/login', headers=headers, json={
            'email': 'nao-existe@example.com',
            'password': 'errada',
        })
        second = client.post('/api/auth/login', headers=headers, json={
            'email': 'nao-existe@example.com',
            'password': 'errada',
        })
        blocked = client.post('/api/auth/login', headers=headers, json={
            'email': 'nao-existe@example.com',
            'password': 'errada',
        })

        assert first.status_code == 401
        assert second.status_code == 401
        assert blocked.status_code == 429
        assert blocked.json()['error'].startswith('Muitas requisicoes')
        assert blocked.headers['retry-after']
        assert blocked.headers['x-ratelimit-limit'] == '2'
        assert blocked.headers['x-ratelimit-remaining'] == '0'
    finally:
        object.__setattr__(settings, 'rate_limit_enabled', original_enabled)
        object.__setattr__(settings, 'rate_limit_auth_per_minute', original_auth)
        object.__setattr__(settings, 'rate_limit_global_per_minute', original_global)
        clear_rate_limit_state()


def test_rate_limit_exempts_health_checks():
    original_enabled = settings.rate_limit_enabled
    original_global = settings.rate_limit_global_per_minute
    try:
        object.__setattr__(settings, 'rate_limit_enabled', True)
        object.__setattr__(settings, 'rate_limit_global_per_minute', 1)
        clear_rate_limit_state()

        first = client.get('/api/health', headers={'X-Forwarded-For': '203.0.113.11'})
        second = client.get('/api/health', headers={'X-Forwarded-For': '203.0.113.11'})

        assert first.status_code == 200
        assert second.status_code == 200
    finally:
        object.__setattr__(settings, 'rate_limit_enabled', original_enabled)
        object.__setattr__(settings, 'rate_limit_global_per_minute', original_global)
        clear_rate_limit_state()


def test_unhandled_exception_returns_generic_json():
    path = '/api/__test/unhandled-error'
    if not any(getattr(route, 'path', None) == path for route in app.routes):
        @app.get(path, include_in_schema=False)
        def raise_unhandled_error():
            raise RuntimeError('segredo sensivel do servidor')
        app.router.routes.insert(0, app.router.routes.pop())

    safe_client = TestClient(app, raise_server_exceptions=False)
    response = safe_client.get(path)

    assert response.status_code == 500
    data = response.json()
    assert data['error'] == 'Erro interno no servidor'
    assert data['error_id']
    assert 'segredo sensivel' not in response.text
    assert 'Traceback' not in response.text


def test_database_url_uses_psycopg_for_postgresql(monkeypatch):
    monkeypatch.setenv(
        'DATABASE_URL',
        'postgresql://user:password@example.neon.tech/neondb?sslmode=require',
    )

    assert database_url() == (
        'postgresql+psycopg://user:password@example.neon.tech/neondb?sslmode=require'
    )


def test_alembic_migrations_create_current_schema():
    from alembic import command
    from alembic.config import Config
    from sqlalchemy import create_engine, inspect

    tmp_root = Path('.tmp')
    tmp_root.mkdir(exist_ok=True)
    db_path = tmp_root / f'migration-{uuid4().hex}.db'
    db_url = f"sqlite:///{db_path.as_posix()}"
    config = Config('alembic.ini')
    config.set_main_option('script_location', 'migrations')
    config.set_main_option('sqlalchemy.url', db_url)
    engine = None

    try:
        command.upgrade(config, 'head')

        engine = create_engine(db_url)
        inspector = inspect(engine)
        tables = set(inspector.get_table_names())
        product_columns = {
            column['name'] for column in inspector.get_columns('products')
        }

        assert {
            'products',
            'product_images',
            'product_imports',
            'users',
            'orders',
            'payments',
            'newsletters',
            'coupons',
            'alembic_version',
        }.issubset(tables)
        assert {'is_active', 'stock_status'}.issubset(product_columns)
    finally:
        if engine is not None:
            engine.dispose()
        for path in tmp_root.glob(f'{db_path.name}*'):
            path.unlink(missing_ok=True)


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


def test_public_catalog_uses_api_cache_instead_of_hardcoded_products():
    products_js = (FRONTEND_ROOT / 'js' / 'products.js').read_text(encoding='utf-8')
    service_worker = (FRONTEND_ROOT / 'service-worker.js').read_text(encoding='utf-8')
    index_html = (FRONTEND_ROOT / 'index.html').read_text(encoding='utf-8')

    assert 'const PRODUCTS' not in products_js
    assert 'Brinco Marguerite' not in products_js
    assert "url.pathname === '/api/products'" in service_worker
    assert 'networkFirstProducts(event.request, event)' in service_worker
    assert 'API_CACHE_NAME' in service_worker
    assert 'apiProducts && apiProducts.length > 0 ? apiProducts : PRODUCTS' not in index_html


def test_admin_frontend_does_not_store_admin_jwt_in_web_storage():
    api_js = (FRONTEND_ROOT / 'js' / 'api.js').read_text(encoding='utf-8')

    assert "sessionStorage.setItem('vj_admin_token'" not in api_js
    assert "localStorage.setItem('vj_admin_token'" not in api_js
    assert "vj_admin_authenticated" in api_js
    assert "credentials: 'include'" in api_js


def test_checkout_has_cep_autofill_wiring():
    api_js = (FRONTEND_ROOT / 'js' / 'api.js').read_text(encoding='utf-8')
    checkout_html = (FRONTEND_ROOT / 'checkout.html').read_text(encoding='utf-8')

    assert 'lookupCep' in api_js
    assert '/address/cep/' in api_js
    assert 'setupCepAutofill()' in checkout_html
    assert 'API.lookupCep' in checkout_html
    assert "setCheckoutField('address', address.street)" in checkout_html


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


def test_order_rejects_invalid_cpf_and_sanitizes_customer_text():
    invalid = client.post('/api/orders', json={
        'customer_name': 'Cliente Teste',
        'customer_email': 'cliente@example.com',
        'customer_cpf': '11111111111',
        'items': [{'id': 1, 'quantity': 1}],
    })
    sanitized = client.post('/api/orders', json={
        'customer_name': '<b>Cliente Seguro</b>',
        'customer_email': 'CLIENTE-SEGURO@EXAMPLE.COM',
        'customer_cpf': '123.456.789-09',
        'customer_phone': '+55 (11) 99999-9999',
        'address_street': '<script>alert(1)</script> Rua Teste',
        'items': [{'id': 1, 'quantity': 1}],
    })

    assert invalid.status_code == 400
    assert 'CPF' in invalid.json()['error']
    assert sanitized.status_code == 201
    data = sanitized.json()
    assert data['customer_name'] == 'Cliente Seguro'
    assert data['customer_email'] == 'cliente-seguro@example.com'
    assert data['customer_cpf'] == '12345678909'
    assert data['customer_phone'] == '11999999999'
    assert '<' not in data['address_street']


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


def test_address_lookup_by_cep_uses_viacep(monkeypatch):
    calls = []

    class CepResponse:
        status_code = 200

        def raise_for_status(self):
            return None

        def json(self):
            return {
                'cep': '01001-000',
                'logradouro': 'Praça da Sé',
                'complemento': 'lado ímpar',
                'bairro': 'Sé',
                'localidade': 'São Paulo',
                'uf': 'SP',
                'ibge': '3550308',
            }

    def fake_get(self, url, timeout):
        calls.append((url, timeout, self.trust_env))
        return CepResponse()

    monkeypatch.setattr('backend.services.address.requests.Session.get', fake_get)

    response = client.get('/api/address/cep/01001-000')

    assert response.status_code == 200
    data = response.json()
    assert data['street'] == 'Praça da Sé'
    assert data['neighborhood'] == 'Sé'
    assert data['city'] == 'São Paulo'
    assert data['state'] == 'SP'
    assert calls == [('https://viacep.com.br/ws/01001000/json/', 5, False)]


def test_address_lookup_rejects_invalid_or_missing_cep(monkeypatch):
    invalid = client.get('/api/address/cep/123')

    class MissingCepResponse:
        status_code = 200

        def raise_for_status(self):
            return None

        def json(self):
            return {'erro': True}

    monkeypatch.setattr(
        'backend.services.address.requests.Session.get',
        lambda self, url, timeout: MissingCepResponse(),
    )
    missing = client.get('/api/address/cep/99999999')

    assert invalid.status_code == 400
    assert missing.status_code == 404


def test_address_lookup_returns_bad_gateway_when_provider_fails(monkeypatch):
    import requests

    def fail_get(self, url, timeout):
        raise requests.Timeout('timeout')

    monkeypatch.setattr('backend.services.address.requests.Session.get', fail_get)

    response = client.get('/api/address/cep/01001000')

    assert response.status_code == 502


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


def test_admin_store_config_requires_admin_token():
    response = client.get('/api/admin/store-config')

    assert response.status_code == 401


def test_admin_can_update_store_config_and_runtime_uses_overrides():
    clear_store_setting_overrides()
    login = admin_login()
    token = login.json()['token']
    headers = {'Authorization': f'Bearer {token}'}
    try:
        update_response = client.put(
            '/api/admin/store-config',
            headers=headers,
            json={
                'values': {
                    'STORE_NAME': 'VJ Teste Admin',
                    'STORE_CATALOG_FILENAME': 'catalogo-admin.pdf',
                    'SHIPPING_MODE': 'fixed',
                    'SHIPPING_FIXED_VALUE': '19.90',
                    'COUPONS_ENABLED': True,
                    'COUPON_CODE': 'ADM15',
                    'COUPON_DISCOUNT_PERCENT': '15',
                    'COUPON_USAGE_LIMIT': '3',
                }
            },
        )
        public_config = client.get('/api/store/config')
        shipping = client.post('/api/shipping/calculate', json={'total': 99.90})
        payment_config = client.get('/api/payments/config')
        coupon = client.post('/api/coupons/validate', json={'code': 'adm15'})
        old_coupon = client.post('/api/coupons/validate', json={'code': 'VJ10'})
        order_with_old_coupon = client.post('/api/orders', json={
            'customer_name': 'Cliente Cupom Antigo',
            'customer_email': 'cupom-antigo@example.com',
            'customer_cpf': '12345678909',
            'items': [{'id': 1, 'quantity': 1}],
            'coupon': 'VJ10',
        })

        assert update_response.status_code == 200
        assert update_response.json()['values']['STORE_NAME'] == 'VJ Teste Admin'
        assert public_config.json()['brand']['name'] == 'VJ Teste Admin'
        assert public_config.json()['catalog']['filename'] == 'catalogo-admin.pdf'
        assert public_config.json()['shipping']['fixed_value'] == 19.9
        assert shipping.json()['shipping'] == 19.9
        assert payment_config.json()['store']['name'] == 'VJ Teste Admin'
        assert coupon.status_code == 200
        assert coupon.json()['discount_percent'] == 15.0
        assert old_coupon.status_code == 404
        assert order_with_old_coupon.status_code == 400
    finally:
        clear_store_setting_overrides()


def test_admin_store_config_rejects_invalid_values():
    login = admin_login()
    token = login.json()['token']
    invalid_shipping = client.put(
        '/api/admin/store-config',
        headers={'Authorization': f'Bearer {token}'},
        json={'values': {'SHIPPING_MODE': 'teleport'}},
    )
    invalid_email = client.put(
        '/api/admin/store-config',
        headers={'Authorization': f'Bearer {token}'},
        json={'values': {'STORE_EMAIL': 'email-invalido'}},
    )

    assert invalid_shipping.status_code == 400
    assert invalid_email.status_code == 400


def test_admin_can_update_order_status():
    login = admin_login()
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


def test_admin_storage_status_does_not_expose_secrets():
    login = admin_login()
    token = login.json()['token']
    response = client.get(
        '/api/admin/storage/status',
        headers={'Authorization': f'Bearer {token}'},
    )

    assert response.status_code == 200
    data = response.json()
    assert data['backend'] == 'local'
    assert 'secret_access_key' not in data['r2']
    assert 'access_key_id' not in data['r2']


def test_admin_login_uses_individual_email_and_records_audit():
    ADMIN_LOGIN_ATTEMPTS.clear()
    with SessionLocal() as db:
        db.query(AdminAuditLog).delete()
        db.commit()

    login = admin_login()
    password_only = client.post(
        '/api/auth/admin/login',
        json={'password': 'test-admin-password'},
    )
    audit_response = client.get(
        '/api/auth/admin/audit-logs',
        headers={'Authorization': f"Bearer {login.json()['token']}"},
    )

    with SessionLocal() as db:
        logs = db.query(AdminAuditLog).order_by(AdminAuditLog.id).all()

    assert login.status_code == 200
    assert login.json()['user']['email'] == ADMIN_EMAIL
    assert password_only.status_code == 401
    assert [log.action for log in logs] == [
        'admin.login.succeeded',
        'admin.login.failed',
    ]
    assert audit_response.status_code == 200
    assert audit_response.json()[0]['action'] in {
        'admin.login.succeeded',
        'admin.login.failed',
    }
    ADMIN_LOGIN_ATTEMPTS.clear()


def test_admin_cookie_is_httponly_and_can_authenticate_admin_routes():
    original_secure = settings.admin_cookie_secure
    cookie_client = TestClient(app)
    try:
        object.__setattr__(settings, 'admin_cookie_secure', False)
        login = admin_login(api_client=cookie_client, persist_cookie=True)
        cookie_response = cookie_client.get('/api/admin/products')
        logout = cookie_client.post('/api/auth/logout')
        after_logout = cookie_client.get('/api/admin/products')

        set_cookie = login.headers.get('set-cookie', '')
        assert login.status_code == 200
        assert f'{settings.admin_cookie_name}=' in set_cookie
        assert 'HttpOnly' in set_cookie
        assert 'SameSite=lax' in set_cookie
        assert cookie_response.status_code == 200
        assert logout.status_code == 200
        assert after_logout.status_code == 401
    finally:
        object.__setattr__(settings, 'admin_cookie_secure', original_secure)


def test_admin_can_create_another_admin_user():
    headers = admin_headers()

    created = client.post(
        '/api/auth/admin/users',
        headers=headers,
        json={
            'name': 'Admin Catalogo',
            'email': 'catalogo-admin@example.com',
            'password': 'senha-admin-forte',
        },
    )
    login = admin_login(
        email='catalogo-admin@example.com',
        password='senha-admin-forte',
    )

    assert created.status_code == 201
    assert created.json()['user']['is_admin'] is True
    assert login.status_code == 200
    assert login.json()['user']['email'] == 'catalogo-admin@example.com'


def test_admin_route_rejects_regular_user_token_even_for_admin_user():
    login = admin_login()
    assert login.status_code == 200

    regular_login = client.post('/api/auth/login', json={
        'email': ADMIN_EMAIL,
        'password': 'test-admin-password',
    })
    token = regular_login.json()['token']

    response = client.get(
        '/api/admin/products',
        headers={'Authorization': f'Bearer {token}'},
    )

    assert regular_login.status_code == 200
    assert response.status_code == 403


def test_admin_login_blocks_repeated_wrong_passwords():
    original_max_attempts = settings.admin_login_max_attempts
    original_lockout = settings.admin_login_lockout_seconds
    ADMIN_LOGIN_ATTEMPTS.clear()
    try:
        object.__setattr__(settings, 'admin_login_max_attempts', 2)
        object.__setattr__(settings, 'admin_login_lockout_seconds', 60)

        first = admin_login(password='errada')
        second = admin_login(password='errada')
        blocked = admin_login()

        assert first.status_code == 401
        assert second.status_code == 401
        assert blocked.status_code == 429
    finally:
        object.__setattr__(settings, 'admin_login_max_attempts', original_max_attempts)
        object.__setattr__(settings, 'admin_login_lockout_seconds', original_lockout)
        ADMIN_LOGIN_ATTEMPTS.clear()


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
    assert response.json()['name'] == 'Brinco Teste'


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


def test_out_of_stock_product_cannot_be_ordered():
    login = admin_login()
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
