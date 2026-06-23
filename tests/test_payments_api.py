from backend.database import SessionLocal
from backend.models import OrderEvent
from tests.helpers import FakeResponse, client, order_payload


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
    assert [event['status'] for event in data['order']['events']] == ['pending', 'paid']
    assert data['order']['events'][-1]['metadata']['provider'] == 'infinitepay'

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
    with SessionLocal() as db:
        events = db.query(OrderEvent).filter_by(order_id=created['order']['id']).all()
        assert [event.status for event in events] == ['pending', 'paid']
        assert events[-1].to_dict()['metadata']['source'] == 'webhook'
