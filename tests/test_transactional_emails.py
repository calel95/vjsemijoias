import re

from backend.services.email import SENT_EMAILS, clear_email_outbox
from tests.helpers import FakeResponse, admin_headers, client, order_payload


def test_registration_sends_welcome_email():
    client.cookies.clear()
    response = client.post('/api/auth/register', json={
        'name': 'Cliente Email',
        'email': 'cliente-email@example.com',
        'password': 'senha123',
        'cpf': '12345678909',
    })

    assert response.status_code == 201
    assert len(SENT_EMAILS) == 1
    assert SENT_EMAILS[0]['to'] == 'cliente-email@example.com'
    assert 'Cadastro recebido' in SENT_EMAILS[0]['subject']


def test_manual_order_sends_order_created_email():
    client.cookies.clear()
    response = client.post('/api/orders', json={
        **order_payload(),
        'customer_email': 'pedido-email@example.com',
    })

    assert response.status_code == 201
    assert len(SENT_EMAILS) == 1
    assert SENT_EMAILS[0]['to'] == 'pedido-email@example.com'
    assert response.json()['id'] in SENT_EMAILS[0]['subject']
    assert 'Acompanhe seu pedido' in SENT_EMAILS[0]['text']


def test_payment_flow_sends_created_and_paid_email_once(monkeypatch):
    client.cookies.clear()

    def fake_request(self, method, url, **kwargs):
        if url.endswith('/links'):
            return FakeResponse({'url': 'https://checkout.infinitepay.com.br/email'})
        return FakeResponse({
            'success': True,
            'paid': True,
            'amount': 14990,
            'paid_amount': 14990,
            'installments': 1,
            'capture_method': 'pix',
        })

    monkeypatch.setattr('backend.infinitepay_client.requests.Session.request', fake_request)
    payload = order_payload()
    payload['customer_email'] = 'pagamento-email@example.com'
    created = client.post('/api/payments/infinitepay/checkout', json=payload)
    order_id = created.json()['order']['id']
    first_confirm = client.post('/api/payments/infinitepay/confirm', json={
        'order_nsu': order_id,
        'transaction_nsu': 'email-transaction-1',
        'slug': 'email-invoice-1',
        'capture_method': 'pix',
    })
    second_confirm = client.post('/api/payments/infinitepay/confirm', json={
        'order_nsu': order_id,
        'transaction_nsu': 'email-transaction-1',
        'slug': 'email-invoice-1',
        'capture_method': 'pix',
    })

    assert created.status_code == 201
    assert first_confirm.status_code == 200
    assert second_confirm.status_code == 200
    subjects = [email['subject'] for email in SENT_EMAILS]
    assert subjects.count(f'Pedido {order_id} recebido - VJ Semijoias') == 1
    assert subjects.count(f'Pagamento aprovado - Pedido {order_id}') == 1


def test_shipped_order_sends_tracking_email():
    client.cookies.clear()
    headers = admin_headers()
    order = client.post('/api/orders', json={
        **order_payload(),
        'customer_email': 'rastreio-email@example.com',
    }).json()
    clear_email_outbox()

    shipped = client.put(
        f"/api/admin/orders/{order['id']}/status",
        headers=headers,
        json={
            'status': 'shipped',
            'tracking_code': 'BR123456789',
            'tracking_carrier': 'Correios',
        },
    )

    assert shipped.status_code == 200
    assert len(SENT_EMAILS) == 1
    assert SENT_EMAILS[0]['to'] == 'rastreio-email@example.com'
    assert 'Pedido ' in SENT_EMAILS[0]['subject']
    assert 'BR123456789' in SENT_EMAILS[0]['text']
    assert 'Correios' in SENT_EMAILS[0]['text']


def test_password_reset_sends_email_and_updates_password():
    client.cookies.clear()
    register = client.post('/api/auth/register', json={
        'name': 'Cliente Reset',
        'email': 'reset-email@example.com',
        'password': 'senha123',
        'cpf': '12345678909',
    })
    clear_email_outbox()

    requested = client.post('/api/auth/password-reset/request', json={
        'email': 'reset-email@example.com',
    })
    token_match = re.search(r'reset_token=([A-Za-z0-9_-]+)', SENT_EMAILS[0]['text'])
    confirmed = client.post('/api/auth/password-reset/confirm', json={
        'token': token_match.group(1),
        'password': 'senha456',
    })
    old_login = client.post('/api/auth/login', json={
        'email': 'reset-email@example.com',
        'password': 'senha123',
    })
    new_login = client.post('/api/auth/login', json={
        'email': 'reset-email@example.com',
        'password': 'senha456',
    })

    assert register.status_code == 201
    assert requested.status_code == 200
    assert token_match
    assert confirmed.status_code == 200
    assert old_login.status_code == 401
    assert new_login.status_code == 200
