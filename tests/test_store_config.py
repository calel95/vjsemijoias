from backend.database import SessionLocal
from backend.models import AdminAuditLog
from backend.store_config import store_settings
from tests.helpers import admin_login, clear_store_setting_overrides, client


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
        assert old_coupon.status_code == 200
        assert order_with_old_coupon.status_code == 201
        with SessionLocal() as db:
            audit = (
                db.query(AdminAuditLog)
                .filter(AdminAuditLog.action == 'store.config.updated')
                .order_by(AdminAuditLog.id.desc())
                .first()
            )
            assert audit is not None
            metadata = audit.to_dict()['metadata']
            assert 'SHIPPING_MODE' in metadata['sensitive_keys']
            assert 'COUPON_CODE' in metadata['sensitive_keys']
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
