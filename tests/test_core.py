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

def test_rate_limit_blocks_mass_registration_by_ip():
    original_enabled = settings.rate_limit_enabled
    original_auth = settings.rate_limit_auth_per_minute
    original_register = settings.rate_limit_register_per_hour
    original_global = settings.rate_limit_global_per_minute
    try:
        object.__setattr__(settings, 'rate_limit_enabled', True)
        object.__setattr__(settings, 'rate_limit_auth_per_minute', 100)
        object.__setattr__(settings, 'rate_limit_register_per_hour', 2)
        object.__setattr__(settings, 'rate_limit_global_per_minute', 100)
        clear_rate_limit_state()

        headers = {'X-Forwarded-For': '203.0.113.12'}
        first = client.post('/api/auth/register', headers=headers, json={
            'name': 'Cliente Rate Limit 1',
            'email': 'rate-limit-register-1@example.com',
            'password': 'senha123',
        })
        second = client.post('/api/auth/register', headers=headers, json={
            'name': 'Cliente Rate Limit 2',
            'email': 'rate-limit-register-2@example.com',
            'password': 'senha123',
        })
        blocked = client.post('/api/auth/register', headers=headers, json={
            'name': 'Cliente Rate Limit 3',
            'email': 'rate-limit-register-3@example.com',
            'password': 'senha123',
        })

        assert first.status_code == 201
        assert second.status_code == 201
        assert blocked.status_code == 429
        assert blocked.json()['error'].startswith('Muitas requisicoes')
        assert blocked.headers['x-ratelimit-limit'] == '2'
        assert int(blocked.headers['retry-after']) > 3000
    finally:
        object.__setattr__(settings, 'rate_limit_enabled', original_enabled)
        object.__setattr__(settings, 'rate_limit_auth_per_minute', original_auth)
        object.__setattr__(settings, 'rate_limit_register_per_hour', original_register)
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
        user_columns = {
            column['name'] for column in inspector.get_columns('users')
        }
        product_columns = {
            column['name'] for column in inspector.get_columns('products')
        }
        product_columns_by_name = {
            column['name']: column for column in inspector.get_columns('products')
        }
        order_columns_by_name = {
            column['name']: column for column in inspector.get_columns('orders')
        }
        payment_columns_by_name = {
            column['name']: column for column in inspector.get_columns('payments')
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
            'coupon_redemptions',
            'order_events',
            'alembic_version',
        }.issubset(tables)
        assert {'is_active', 'stock_status'}.issubset(product_columns)
        assert {
            'password_reset_token_hash',
            'password_reset_expires_at',
        }.issubset(user_columns)
        assert isinstance(product_columns_by_name['price']['type'], Numeric)
        assert isinstance(product_columns_by_name['oldPrice']['type'], Numeric)
        assert isinstance(order_columns_by_name['total']['type'], Numeric)
        assert isinstance(coupon_columns_by_name['discount_percent']['type'], Numeric)
        assert isinstance(coupon_columns_by_name['discount_value']['type'], Numeric)
        assert {
            'discount_type',
            'minimum_subtotal',
            'per_customer_limit',
            'starts_at',
            'ends_at',
        }.issubset(coupon_columns_by_name)
        assert {
            'sku',
            'reference',
            'stock_quantity',
            'low_stock_alert',
            'weight_grams',
            'height_cm',
            'width_cm',
            'length_cm',
            'shipping_profile',
        }.issubset(product_columns)
        assert 'stock_deducted' in order_columns_by_name
        assert {
            'idempotency_key',
            'public_token',
            'tracking_code',
            'tracking_carrier',
            'shipped_at',
            'delivered_at',
            'shipping_provider',
            'shipping_service',
            'shipping_estimated_days',
            'shipping_destination_zip',
            'shipping_option_id',
            'shipping_company_id',
            'shipping_company',
        }.issubset(order_columns_by_name)
        assert 'checkout_url' in payment_columns_by_name
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
    order_tracking_response = client.get('/pedido')

    assert index_response.status_code == 200
    assert b'VJ Semijoias' in index_response.content
    assert css_response.status_code == 200
    assert admin_response.status_code == 200
    assert b'<!DOCTYPE html>' in admin_response.content
    assert legacy_catalog_response.status_code == 200
    assert manifest_response.status_code == 200
    assert service_worker_response.status_code == 200
    assert order_tracking_response.status_code == 200
    assert b'Acompanhe seu pedido' in order_tracking_response.content

def test_public_catalog_uses_api_cache_instead_of_hardcoded_products():
    products_js = (FRONTEND_ROOT / 'js' / 'products.js').read_text(encoding='utf-8')
    service_worker = (FRONTEND_ROOT / 'service-worker.js').read_text(encoding='utf-8')
    index_html = (FRONTEND_ROOT / 'index.html').read_text(encoding='utf-8')

    assert 'const PRODUCTS' not in products_js
    assert 'Brinco Marguerite' not in products_js
    assert "url.pathname === '/api/products'" in service_worker
    assert 'networkFirstProducts(event.request, event)' in service_worker
    assert 'productsFromPayload(payload)' in service_worker
    assert 'API_CACHE_NAME' in service_worker
    assert 'apiProducts && apiProducts.length > 0 ? apiProducts : PRODUCTS' not in index_html

def test_home_uses_paginated_featured_products():
    index_html = (FRONTEND_ROOT / 'index.html').read_text(encoding='utf-8')
    products_js = (FRONTEND_ROOT / 'js' / 'products.js').read_text(encoding='utf-8')
    api_js = (FRONTEND_ROOT / 'js' / 'api.js').read_text(encoding='utf-8')

    assert 'loadProductsPageFromAPI({ page: 1, perPage: 8 })' in index_html
    assert 'page=${encodeURIComponent(options.page)}' in api_js
    assert 'per_page=${encodeURIComponent(options.perPage)}' in api_js
    assert 'Array.isArray(data.items)' in products_js

def test_admin_panel_is_split_into_pages():
    admin_html = (FRONTEND_ROOT / 'admin.html').read_text(encoding='utf-8')
    admin_js = (FRONTEND_ROOT / 'js' / 'admin.js').read_text(encoding='utf-8')
    admin_css = (FRONTEND_ROOT / 'css' / 'admin.css').read_text(encoding='utf-8')

    for page in ['overview', 'orders', 'settings', 'contacts', 'coupons', 'security', 'products', 'catalog', 'import']:
        assert f'data-admin-page="{page}"' in admin_html
        assert f'data-admin-page-target="{page}"' in admin_html
    assert 'admin-page-nav' in admin_html
    assert 'admin-pages' in admin_html
    assert 'switchAdminPage' in admin_js
    assert 'ADMIN_PAGES' in admin_js
    assert '.admin-page.active' in admin_css
def test_admin_product_form_exposes_shipping_dimensions():
    admin_html = (FRONTEND_ROOT / 'admin.html').read_text(encoding='utf-8')
    admin_js = (FRONTEND_ROOT / 'js' / 'admin.js').read_text(encoding='utf-8')

    assert 'product-weight-grams' in admin_html
    assert 'product-height-cm' in admin_html
    assert 'product-width-cm' in admin_html
    assert 'product-length-cm' in admin_html
    assert 'product-shipping-profile' in admin_html
    assert 'weight_grams' in admin_js
    assert 'shipping_profile' in admin_js

def test_frontend_shipping_calculation_sends_cart_items():
    api_js = (FRONTEND_ROOT / 'js' / 'api.js').read_text(encoding='utf-8')
    cart_js = (FRONTEND_ROOT / 'js' / 'cart.js').read_text(encoding='utf-8')
    product_html = (FRONTEND_ROOT / 'produto.html').read_text(encoding='utf-8')
    cart_html = (FRONTEND_ROOT / 'carrinho.html').read_text(encoding='utf-8')
    checkout_html = (FRONTEND_ROOT / 'checkout.html').read_text(encoding='utf-8')

    assert 'async calculateShipping(total, zipCode = \'\', items = [])' in api_js
    assert 'payload.items = items.map' in api_js
    assert 'API.calculateShipping(subtotal, cepDigits, this.items)' in cart_js
    assert 'CART_PRICING_KEY' in cart_js
    assert 'setShippingQuote' in cart_js
    assert 'selectShippingOption' in cart_js
    assert 'product-shipping-cep' in product_html
    assert 'calculateProductShipping()' in product_html
    assert 'setupProductShippingCalculator()' in product_html
    assert 'API.calculateShipping(' in product_html
    assert '[{ id: product.id, quantity }]' in product_html
    assert 'cart-shipping-cep' in cart_html
    assert 'calculateCartShipping()' in cart_html
    assert 'selectCartShippingOption' in cart_html
    assert 'goToCheckoutFromCart(event)' in cart_html
    assert 'Calcule pelo CEP' in cart_html
    assert 'cart-shipping-option' in cart_html
    assert 'checkout-shipping-summary' in checkout_html
    assert 'Cart.getShippingZipCode()' in checkout_html
    assert 'shipping_option_id: Cart.pricing.shippingOption?.id || checkoutSelectedShippingId' in checkout_html

def test_order_tracking_page_and_admin_modal_are_wired():
    pedido_html = (FRONTEND_ROOT / 'pedido.html').read_text(encoding='utf-8')
    admin_html = (FRONTEND_ROOT / 'admin.html').read_text(encoding='utf-8')
    admin_js = (FRONTEND_ROOT / 'js' / 'admin.js').read_text(encoding='utf-8')
    api_js = (FRONTEND_ROOT / 'js' / 'api.js').read_text(encoding='utf-8')
    service_worker = (FRONTEND_ROOT / 'service-worker.js').read_text(encoding='utf-8')

    assert 'order-tracking-form' in pedido_html
    assert 'API.getPublicOrder(orderId, token)' in pedido_html
    assert 'API.lookupPublicOrder' in pedido_html
    assert "'/pedido'" in service_worker
    assert 'lookupPublicOrder(orderData)' in api_js
    assert 'order-modal' in admin_html
    assert 'openOrderModal' in admin_js
    assert 'saveOrderModal' in admin_js
    assert 'EMAIL_BACKEND' in admin_html
    assert 'email-test-recipient' in admin_html
    assert 'sendTestEmail' in admin_js
    assert 'sendAdminEmailTest(email)' in api_js
    assert "window.prompt('Codigo de rastreio:'" not in admin_js
    assert "window.prompt('Transportadora:'" not in admin_js

def test_checkout_uses_cart_shipping_without_recalculating_on_cep():
    checkout_html = (FRONTEND_ROOT / 'checkout.html').read_text(encoding='utf-8')

    assert 'checkout-shipping-options' not in checkout_html
    assert 'checkoutShippingOptions' not in checkout_html
    assert 'renderShippingOptionsHTML' not in checkout_html
    assert 'selectCheckoutShippingOption' not in checkout_html
    assert 'refreshCheckoutShippingOptions' not in checkout_html
    assert 'Frete selecionado' in checkout_html
    assert 'Escolha o frete no carrinho antes de continuar' in checkout_html
    assert 'O CEP do endereco mudou. Recalcule o frete no carrinho.' in checkout_html
    assert 'shipping_option_id: Cart.pricing.shippingOption?.id || checkoutSelectedShippingId' in checkout_html

def test_catalog_loads_categories_from_api():
    catalog_html = (FRONTEND_ROOT / 'catalogo.html').read_text(encoding='utf-8')
    products_js = (FRONTEND_ROOT / 'js' / 'products.js').read_text(encoding='utf-8')
    api_js = (FRONTEND_ROOT / 'js' / 'api.js').read_text(encoding='utf-8')

    assert 'loadCategoriesFromAPI()' in catalog_html
    assert 'async getCategories()' in api_js
    assert 'categoriesLoaded' in products_js
    assert 'normalizeCategories' in products_js

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

def test_checkout_and_admin_have_order_flow_hardening_wiring():
    checkout_html = (FRONTEND_ROOT / 'checkout.html').read_text(encoding='utf-8')
    admin_js = (FRONTEND_ROOT / 'js' / 'admin.js').read_text(encoding='utf-8')
    api_js = (FRONTEND_ROOT / 'js' / 'api.js').read_text(encoding='utf-8')

    assert 'vj_checkout_idempotency_key' in checkout_html
    assert 'idempotency_key: getCheckoutIdempotencyKey()' in checkout_html
    assert 'payment_pending' in admin_js
    assert 'tracking_code' in admin_js
    assert 'getPublicOrder' in api_js

def test_admin_frontend_has_stock_management_fields():
    admin_html = (FRONTEND_ROOT / 'admin.html').read_text(encoding='utf-8')
    admin_js = (FRONTEND_ROOT / 'js' / 'admin.js').read_text(encoding='utf-8')

    assert 'product-reference' in admin_html
    assert 'product-sku' in admin_html
    assert 'product-stock-quantity' in admin_html
    assert 'product-low-stock-alert' in admin_html
    assert 'reference' in admin_js
    assert 'stock_is_low' in admin_js

def test_admin_frontend_renders_order_event_timeline():
    admin_js = (FRONTEND_ROOT / 'js' / 'admin.js').read_text(encoding='utf-8')
    admin_css = (FRONTEND_ROOT / 'css' / 'admin.css').read_text(encoding='utf-8')

    assert 'orderEventsTimeline(order)' in admin_js
    assert 'order-events-timeline' in admin_css

def test_admin_frontend_has_admin_security_panel():
    admin_html = (FRONTEND_ROOT / 'admin.html').read_text(encoding='utf-8')
    admin_js = (FRONTEND_ROOT / 'js' / 'admin.js').read_text(encoding='utf-8')
    api_js = (FRONTEND_ROOT / 'js' / 'api.js').read_text(encoding='utf-8')

    assert 'admin-user-form' in admin_html
    assert 'admin-audit-list' in admin_html
    assert 'loadAdminSecurity()' in admin_js
    assert 'getAdminUsers()' in api_js

def test_admin_settings_and_contacts_pages_are_split():
    admin_html = (FRONTEND_ROOT / 'admin.html').read_text(encoding='utf-8')
    admin_js = (FRONTEND_ROOT / 'js' / 'admin.js').read_text(encoding='utf-8')
    store_config_js = (FRONTEND_ROOT / 'js' / 'store-config.js').read_text(encoding='utf-8')
    index_html = (FRONTEND_ROOT / 'index.html').read_text(encoding='utf-8')

    settings_section = admin_html.split('id="admin-page-settings"', 1)[1].split('id="admin-page-contacts"', 1)[0]
    contacts_section = admin_html.split('id="admin-page-contacts"', 1)[1].split('id="admin-page-coupons"', 1)[0]

    assert 'STORE_CATALOG_TITLE' not in admin_html
    assert 'STORE_CATALOG_COLLECTION' not in admin_html
    assert 'STORE_CATALOG_FILENAME' not in admin_html
    assert 'STORE_NAME' not in admin_html
    assert 'STORE_DESCRIPTION' not in admin_html
    assert 'STORE_EMAIL' not in settings_section
    assert 'STORE_EMAIL' in contacts_section
    assert 'STORE_LOCATION' in contacts_section
    assert 'STORE_BUSINESS_HOURS' in contacts_section
    assert 'settings-admin-grid' in admin_html
    assert 'renderContactConfigPreview' in admin_js
    assert 'data-store-location' in store_config_js
    assert 'data-store-hours' in store_config_js
    assert 'data-store-location' in index_html
    assert 'data-store-hours' in index_html

def test_admin_frontend_has_coupon_management_panel():
    admin_html = (FRONTEND_ROOT / 'admin.html').read_text(encoding='utf-8')
    admin_js = (FRONTEND_ROOT / 'js' / 'admin.js').read_text(encoding='utf-8')
    api_js = (FRONTEND_ROOT / 'js' / 'api.js').read_text(encoding='utf-8')

    assert 'admin-coupon-form' in admin_html
    assert 'coupon-per-customer-limit' in admin_html
    assert 'data-store-config="COUPON_CODE"' not in admin_html
    assert 'data-store-config="COUPON_DISCOUNT_PERCENT"' not in admin_html
    assert 'data-store-config="COUPON_USAGE_LIMIT"' not in admin_html
    assert 'data-store-config="SHIPPING_PROVIDER"' in admin_html
    assert 'data-store-config="MELHOR_ENVIO_FROM_POSTAL_CODE"' in admin_html
    assert 'data-store-config="MELHOR_ENVIO_SERVICES"' in admin_html
    assert 'data-store-config="MELHOR_ENVIO_ALLOWED_COMPANY_IDS"' in admin_html
    assert 'data-store-config="MELHOR_ENVIO_TIMEOUT_SECONDS"' in admin_html
    assert 'loadAdminCoupons()' in admin_js
    assert 'createAdminCoupon' in api_js
    assert 'updateAdminCoupon' in api_js
    assert 'getAdminAuditLogs' in api_js
