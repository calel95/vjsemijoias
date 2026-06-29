from backend.database import SessionLocal
from backend.models import AdminAuditLog
from backend.store_config import store_settings
from backend.services.email import SENT_EMAILS, current_email_config
from tests.helpers import admin_headers, admin_login, clear_store_setting_overrides, client


def test_store_config_exposes_shipping_and_coupon_settings():
    response = client.get('/api/store/config')

    assert response.status_code == 200
    data = response.json()
    assert data['brand']['name'] == 'VJ Semijoias'
    assert data['contact']['instagram'] == 'vj_semijoias'
    assert data['contact']['location'] == 'Canoas - RS'
    assert data['contact']['business_hours'] == 'Seg-Sex: 9h as 18h'
    assert data['catalog']['filename'] == 'catalogo-vj-semijoias.pdf'
    assert data['shipping']['mode'] == 'free'
    assert 'provider' not in data['shipping']
    assert 'melhor_envio_from_postal_code' not in data['shipping']
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
                    'STORE_LOCATION': 'Porto Alegre - RS',
                    'STORE_BUSINESS_HOURS': 'Seg-Sab: 10h as 19h',
                    'SHIPPING_MODE': 'fixed',
                    'SHIPPING_FIXED_VALUE': '19.90',
                    'SHIPPING_PROVIDER': 'melhor_envio',
                    'MELHOR_ENVIO_FROM_POSTAL_CODE': '92310-120',
                    'MELHOR_ENVIO_SERVICES': '1, 2',
                    'MELHOR_ENVIO_ALLOWED_COMPANY_IDS': '1, 2, 14',
                    'MELHOR_ENVIO_TIMEOUT_SECONDS': '8.5',
                    'COUPONS_ENABLED': True,
                    'COUPON_CODE': 'ADM15',
                    'COUPON_DISCOUNT_PERCENT': '15',
                    'COUPON_USAGE_LIMIT': '3',
                    'EMAIL_FROM_NAME': 'VJ Admin Email',
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
        assert public_config.json()['contact']['location'] == 'Porto Alegre - RS'
        assert public_config.json()['contact']['business_hours'] == 'Seg-Sab: 10h as 19h'
        assert public_config.json()['shipping']['fixed_value'] == 19.9
        assert 'provider' not in public_config.json()['shipping']
        assert update_response.json()['values']['SHIPPING_PROVIDER'] == 'melhor_envio'
        assert update_response.json()['values']['MELHOR_ENVIO_FROM_POSTAL_CODE'] == '92310120'
        assert update_response.json()['values']['MELHOR_ENVIO_SERVICES'] == '1,2'
        assert update_response.json()['values']['MELHOR_ENVIO_ALLOWED_COMPANY_IDS'] == '1,2,14'
        assert update_response.json()['values']['MELHOR_ENVIO_TIMEOUT_SECONDS'] == '8.5'
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
            assert 'SHIPPING_PROVIDER' in metadata['sensitive_keys']
            assert 'COUPON_CODE' in metadata['sensitive_keys']
            assert 'EMAIL_FROM_NAME' in metadata['sensitive_keys']
    finally:
        clear_store_setting_overrides()

def test_admin_can_update_email_config_and_send_test_email():
    clear_store_setting_overrides()
    login = admin_login()
    headers = {'Authorization': f"Bearer {login.json()['token']}"}
    try:
        update_response = client.put(
            '/api/admin/store-config',
            headers=headers,
            json={
                'values': {
                    'EMAIL_FROM_NAME': 'VJ Admin Email',
                    'EMAIL_FROM_NAME': 'VJ Atendimento',
                    'EMAIL_FROM_ADDRESS': 'atendimento@example.com',
                    'EMAIL_SMTP_HOST': 'smtp.example.com',
                    'EMAIL_SMTP_PORT': '2525',
                    'EMAIL_SMTP_USERNAME': 'smtp-user',
                    'EMAIL_SMTP_PASSWORD': 'smtp-secret',
                    'EMAIL_SMTP_USE_TLS': False,
                }
            },
        )
        config = current_email_config()
        test_response = client.post(
            '/api/admin/store-config/email-test',
            headers=headers,
            json={'email': 'teste-email@example.com'},
        )

        assert update_response.status_code == 200
        values = update_response.json()['values']
        assert values['EMAIL_BACKEND'] == 'console'
        assert values['EMAIL_FROM_ADDRESS'] == 'atendimento@example.com'
        assert values['EMAIL_SMTP_PASSWORD'] == ''
        assert config.from_address == 'atendimento@example.com'
        assert config.smtp_password == 'smtp-secret'
        assert test_response.status_code == 200
        assert SENT_EMAILS[-1]['to'] == 'teste-email@example.com'
        assert SENT_EMAILS[-1]['backend'] == 'console'
        assert 'VJ Atendimento' in SENT_EMAILS[-1]['from']
    finally:
        clear_store_setting_overrides()


def test_admin_store_config_keeps_existing_smtp_password_when_blank():
    clear_store_setting_overrides()
    login = admin_login()
    headers = {'Authorization': f"Bearer {login.json()['token']}"}
    try:
        first = client.put(
            '/api/admin/store-config',
            headers=headers,
            json={'values': {'EMAIL_SMTP_PASSWORD': 'senha-inicial'}},
        )
        second = client.put(
            '/api/admin/store-config',
            headers=headers,
            json={'values': {'EMAIL_FROM_NAME': 'Novo Nome', 'EMAIL_SMTP_PASSWORD': ''}},
        )

        assert first.status_code == 200
        assert second.status_code == 200
        assert current_email_config().smtp_password == 'senha-inicial'
        assert second.json()['values']['EMAIL_SMTP_PASSWORD'] == ''
    finally:
        clear_store_setting_overrides()


def test_admin_threshold_shipping_charges_below_minimum_and_free_above():
    clear_store_setting_overrides()
    headers = admin_headers()
    try:
        update = client.put(
            '/api/admin/store-config',
            headers=headers,
            json={'values': {
                'SHIPPING_MODE': 'threshold',
                'SHIPPING_FIXED_VALUE': '19.90',
                'SHIPPING_FREE_MINIMUM': '300',
                'SHIPPING_PROVIDER': 'internal',
            }},
        )
        below = client.post('/api/shipping/calculate', json={
            'total': 99.90,
            'zip_code': '01001000',
        })
        above = client.post('/api/shipping/calculate', json={
            'total': 300.00,
            'zip_code': '01001000',
        })

        assert update.status_code == 200
        assert below.status_code == 200
        assert below.json()['shipping'] == 19.9
        assert below.json()['selected_option']['service'] == 'Frete fixo'
        assert above.status_code == 200
        assert above.json()['shipping'] == 0
        assert above.json()['selected_option']['service'] == 'Frete gratis'
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
    invalid_provider = client.put(
        '/api/admin/store-config',
        headers={'Authorization': f'Bearer {token}'},
        json={'values': {'SHIPPING_PROVIDER': 'transportadora-magica'}},
    )
    invalid_email_backend = client.put(
        '/api/admin/store-config',
        headers={'Authorization': f'Bearer {token}'},
        json={'values': {'EMAIL_BACKEND': 'fax'}},
    )
    invalid_smtp_port = client.put(
        '/api/admin/store-config',
        headers={'Authorization': f'Bearer {token}'},
        json={'values': {'EMAIL_SMTP_PORT': '99999'}},
    )
    invalid_threshold_zero_shipping = client.put(
        '/api/admin/store-config',
        headers={'Authorization': f'Bearer {token}'},
        json={'values': {
            'SHIPPING_MODE': 'threshold',
            'SHIPPING_FIXED_VALUE': '0',
            'SHIPPING_FREE_MINIMUM': '300',
            'SHIPPING_PROVIDER': 'internal',
        }},
    )
    invalid_origin_zip = client.put(
        '/api/admin/store-config',
        headers={'Authorization': f'Bearer {token}'},
        json={'values': {'MELHOR_ENVIO_FROM_POSTAL_CODE': '123'}},
    )

    assert invalid_shipping.status_code == 400
    assert invalid_email.status_code == 400
    assert invalid_provider.status_code == 400
    assert invalid_email_backend.status_code == 400
    assert invalid_smtp_port.status_code == 400
    assert invalid_threshold_zero_shipping.status_code == 400
    assert invalid_origin_zip.status_code == 400
