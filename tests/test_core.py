from uuid import uuid4
from pathlib import Path

from fastapi.testclient import TestClient

from backend.app import app
from backend.config import FRONTEND_ROOT, database_url, settings
from backend.services.rate_limit import clear_rate_limit_state
from tests.helpers import client


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
    from sqlalchemy import Numeric, create_engine, inspect

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
        product_columns_by_name = {
            column['name']: column for column in inspector.get_columns('products')
        }
        order_columns_by_name = {
            column['name']: column for column in inspector.get_columns('orders')
        }
        coupon_columns_by_name = {
            column['name']: column for column in inspector.get_columns('coupons')
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
            'order_events',
            'alembic_version',
        }.issubset(tables)
        assert {'is_active', 'stock_status'}.issubset(product_columns)
        assert isinstance(product_columns_by_name['price']['type'], Numeric)
        assert isinstance(product_columns_by_name['oldPrice']['type'], Numeric)
        assert isinstance(order_columns_by_name['total']['type'], Numeric)
        assert isinstance(coupon_columns_by_name['discount_percent']['type'], Numeric)
        assert {'sku', 'stock_quantity', 'low_stock_alert'}.issubset(product_columns)
        assert 'stock_deducted' in order_columns_by_name
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

def test_frontend_does_not_store_user_jwt_in_local_storage():
    api_js = (FRONTEND_ROOT / 'js' / 'api.js').read_text(encoding='utf-8')

    assert "localStorage.setItem('vj_api_token'" not in api_js
    assert "headers['Authorization']" not in api_js
    assert "credentials: 'include'" in api_js
    assert "csrfCookieName: 'vj_csrf_token'" in api_js
    assert "csrfHeaderName: 'X-CSRF-Token'" in api_js
    assert 'getCsrfHeaders(method)' in api_js

def test_checkout_has_cep_autofill_wiring():
    api_js = (FRONTEND_ROOT / 'js' / 'api.js').read_text(encoding='utf-8')
    checkout_html = (FRONTEND_ROOT / 'checkout.html').read_text(encoding='utf-8')

    assert 'lookupCep' in api_js
    assert '/address/cep/' in api_js
    assert 'setupCepAutofill()' in checkout_html
    assert 'API.lookupCep' in checkout_html
    assert "setCheckoutField('address', address.street)" in checkout_html

def test_admin_frontend_has_stock_management_fields():
    admin_html = (FRONTEND_ROOT / 'admin.html').read_text(encoding='utf-8')
    admin_js = (FRONTEND_ROOT / 'js' / 'admin.js').read_text(encoding='utf-8')

    assert 'product-sku' in admin_html
    assert 'product-stock-quantity' in admin_html
    assert 'product-low-stock-alert' in admin_html
    assert 'stock_is_low' in admin_js

def test_admin_frontend_renders_order_event_timeline():
    admin_js = (FRONTEND_ROOT / 'js' / 'admin.js').read_text(encoding='utf-8')
    admin_css = (FRONTEND_ROOT / 'css' / 'admin.css').read_text(encoding='utf-8')

    assert 'orderEventsTimeline(order)' in admin_js
    assert 'order-events-timeline' in admin_css
