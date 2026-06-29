from tests.helpers import admin_headers, client, order_payload


def test_admin_can_create_percent_and_fixed_coupons():
    headers = admin_headers()
    percent_response = client.post(
        '/api/admin/coupons',
        headers=headers,
        json={
            'code': 'MINIMO25',
            'discount_type': 'percent',
            'discount_value': '25',
            'minimum_subtotal': '100',
            'usage_limit': 10,
            'per_customer_limit': 0,
            'is_active': True,
        },
    )
    fixed_response = client.post(
        '/api/admin/coupons',
        headers=headers,
        json={
            'code': 'FIXO30',
            'discount_type': 'fixed',
            'discount_value': '30',
            'minimum_subtotal': '0',
            'usage_limit': 10,
            'per_customer_limit': 0,
            'is_active': True,
        },
    )
    below_minimum = client.post(
        '/api/coupons/validate',
        json={'code': 'MINIMO25', 'total': 80},
    )
    percent_validate = client.post(
        '/api/coupons/validate',
        json={'code': 'MINIMO25', 'total': 200},
    )
    fixed_validate = client.post(
        '/api/coupons/validate',
        json={'code': 'FIXO30', 'total': 149.90},
    )

    assert percent_response.status_code == 201
    assert percent_response.json()['discount_type'] == 'percent'
    assert fixed_response.status_code == 201
    assert fixed_response.json()['discount_type'] == 'fixed'
    assert below_minimum.status_code == 404
    assert percent_validate.status_code == 200
    assert percent_validate.json()['discount'] == 50.0
    assert fixed_validate.status_code == 200
    assert fixed_validate.json()['discount'] == 30.0


def test_coupon_per_customer_limit_and_usage_report():
    headers = admin_headers()
    create_response = client.post(
        '/api/admin/coupons',
        headers=headers,
        json={
            'code': 'CPF1',
            'discount_type': 'percent',
            'discount_value': '10',
            'minimum_subtotal': '0',
            'usage_limit': 5,
            'per_customer_limit': 1,
            'is_active': True,
        },
    )
    payload = order_payload()
    payload['customer_email'] = 'limite-cupom@example.com'
    payload['customer_cpf'] = '12345678909'
    payload['coupon'] = 'CPF1'

    first_order = client.post('/api/orders', json=payload)
    second_order = client.post('/api/orders', json=payload)
    report = client.get('/api/admin/coupons', headers=headers)
    coupon_report = next(item for item in report.json() if item['code'] == 'CPF1')

    assert create_response.status_code == 201
    assert first_order.status_code == 201
    assert second_order.status_code == 400
    assert 'utilizado' in second_order.json()['error']
    assert coupon_report['used_count'] == 1
    assert coupon_report['redemptions'][0]['customer_email'] == 'limite-cupom@example.com'
