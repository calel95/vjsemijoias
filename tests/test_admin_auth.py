from fastapi.testclient import TestClient

from backend.app import ADMIN_LOGIN_ATTEMPTS, app
from backend.config import settings
from backend.database import SessionLocal
from backend.models import AdminAuditLog
from tests.helpers import ADMIN_EMAIL, admin_headers, admin_login, client


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
