from decimal import Decimal

from backend.database import SessionLocal
from backend.models import Order, OrderEvent, Product
from tests.helpers import admin_login, client


def test_catalog_has_seed_products():
    response = client.get('/api/products')

    assert response.status_code == 200
    products = response.json()
    assert len(products) >= 10
    assert any(product['custom'] is False for product in products)

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
    assert order['events'][0]['event_type'] == 'order.status.pending'
    assert order['events'][0]['message'] == 'Pedido criado'

    with SessionLocal() as db:
        stored = db.get(Order, order['id'])
        assert stored.subtotal == Decimal('299.80')
        assert stored.discount == Decimal('29.98')
        assert stored.total == Decimal('269.82')
        events = db.query(OrderEvent).filter_by(order_id=order['id']).all()
        assert [event.status for event in events] == ['pending']

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
    assert [event['status'] for event in updated.json()['events']] == ['pending', 'processing']
    assert invalid.status_code == 400

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

def test_paid_order_deducts_stock_once_and_blocks_oversell():
    token = admin_login().json()['token']
    created = client.post(
        '/api/products',
        headers={'Authorization': f'Bearer {token}'},
        json={
            'name': 'Produto Baixa Estoque',
            'category': 'aneis',
            'price': 80,
            'description': 'Produto para baixa de estoque.',
            'stock_quantity': 1,
            'low_stock_alert': 1,
        },
    ).json()

    blocked = client.post('/api/orders', json={
        'customer_name': 'Cliente Estoque',
        'customer_email': 'estoque-bloqueado@example.com',
        'customer_cpf': '12345678909',
        'items': [{'id': created['id'], 'quantity': 2}],
    })
    order_response = client.post('/api/orders', json={
        'customer_name': 'Cliente Estoque',
        'customer_email': 'estoque@example.com',
        'customer_cpf': '12345678909',
        'items': [{'id': created['id'], 'quantity': 1}],
    })
    order_id = order_response.json()['id']
    paid_once = client.put(
        f'/api/admin/orders/{order_id}/status',
        headers={'Authorization': f'Bearer {token}'},
        json={'status': 'paid'},
    )
    paid_twice = client.put(
        f'/api/admin/orders/{order_id}/status',
        headers={'Authorization': f'Bearer {token}'},
        json={'status': 'paid'},
    )
    after_stock = client.get(
        '/api/admin/products',
        headers={'Authorization': f'Bearer {token}'},
    ).json()
    product = next(item for item in after_stock if item['id'] == created['id'])

    assert blocked.status_code == 400
    assert 'estoque' in blocked.json()['error'].lower()
    assert order_response.status_code == 201
    assert paid_once.status_code == 200
    assert paid_twice.status_code == 200
    assert paid_twice.json()['stock_deducted'] is True
    assert [event['status'] for event in paid_twice.json()['events']] == ['pending', 'paid']
    assert product['stock_quantity'] == 0
    assert product['stock_status'] == 'out_of_stock'
