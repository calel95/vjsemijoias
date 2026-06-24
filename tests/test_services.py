from types import SimpleNamespace

import pytest

from backend.database import SessionLocal
from backend.services.orders import (
    calculate_order,
    configured_shipping,
    money,
    normalize_order_status,
    validate_order_data,
)
from backend.services.payments import cents, public_url, update_infinitepay_payment
from backend.services.product_media import (
    normalize_stock_status,
    product_image_list,
    store_admin_gallery_images,
    storage_slug,
)
from backend.services.shipping import build_shipping_package, normalize_zip
from backend.services.storage import upload_r2_object
from backend.services.validation import (
    clean_text,
    normalize_email,
    normalize_phone,
    validate_cpf,
    validate_image_bytes,
)
from backend.store_config import store_settings
from tests.helpers import TINY_GIF


def test_money_rounds_and_rejects_invalid_values():
    assert money('10.005') == money('10.01')
    assert money(19.9) == money('19.90')

    with pytest.raises(ValueError, match='monet'):
        money('nao-e-numero')


def test_configured_shipping_threshold_mode():
    original_mode = store_settings.shipping.mode
    original_value = store_settings.shipping.fixed_value
    original_minimum = store_settings.shipping.free_minimum
    try:
        object.__setattr__(store_settings.shipping, 'mode', 'threshold')
        object.__setattr__(store_settings.shipping, 'fixed_value', '19.90')
        object.__setattr__(store_settings.shipping, 'free_minimum', '200')

        below = configured_shipping('149.90')
        above = configured_shipping('200.00')

        assert below['shipping'] == money('19.90')
        assert 'Frete fixo' in below['message']
        assert above['shipping'] == money('0')
        assert 'gratis acima' in above['message']
    finally:
        object.__setattr__(store_settings.shipping, 'mode', original_mode)
        object.__setattr__(store_settings.shipping, 'fixed_value', original_value)
        object.__setattr__(store_settings.shipping, 'free_minimum', original_minimum)


def test_configured_shipping_returns_provider_option_details():
    shipping = configured_shipping('149.90', zip_code='01001-000')

    assert shipping['provider'] == 'internal'
    assert shipping['service']
    assert shipping['estimated_days']
    assert shipping['destination_zip'] == '01001000'


def test_normalize_zip_accepts_empty_and_rejects_invalid_values():
    assert normalize_zip('') == ''
    assert normalize_zip('01001-000') == '01001000'

    with pytest.raises(ValueError, match='CEP'):
        normalize_zip('123')


def test_build_shipping_package_stacks_height_and_sums_weight():
    product_a = SimpleNamespace(
        weight_grams=120,
        height_cm=money('2.50'),
        width_cm=money('8'),
        length_cm=money('12'),
        shipping_profile='caixa-p',
    )
    product_b = SimpleNamespace(
        weight_grams=80,
        height_cm=money('1.50'),
        width_cm=money('9'),
        length_cm=money('10'),
        shipping_profile='caixa-p',
    )

    package = build_shipping_package([(product_a, 2), (product_b, 1)])

    assert package['item_count'] == 3
    assert package['weight_grams'] == 320
    assert package['height_cm'] == money('6.50')
    assert package['width_cm'] == money('9')
    assert package['length_cm'] == money('12')
    assert package['shipping_profile'] == 'caixa-p'


def test_calculate_order_merges_quantities_and_applies_coupon():
    with SessionLocal() as db:
        totals = calculate_order(
            db,
            [{'id': 1, 'quantity': 1}, {'id': 1, 'quantity': 2}],
            'vj10',
            zip_code='01001-000',
        )

    assert len(totals['items']) == 1
    assert totals['items'][0]['quantity'] == 3
    assert totals['subtotal'] == money('449.70')
    assert totals['discount'] == money('44.97')
    assert totals['total'] == money('404.73')
    assert totals['coupon'] == 'VJ10'
    assert totals['shipping_provider'] == 'internal'
    assert totals['shipping_destination_zip'] == '01001000'


def test_validate_order_data_rejects_missing_and_invalid_customer_fields():
    with SessionLocal() as db:
        with pytest.raises(ValueError, match='customer_email'):
            validate_order_data(db, {'customer_name': 'Cliente'})

        with pytest.raises(ValueError, match='E-mail'):
            validate_order_data(
                db,
                {
                    'customer_name': 'Cliente',
                    'customer_email': 'email-invalido',
                    'customer_cpf': '12345678909',
                    'items': [{'id': 1, 'quantity': 1}],
                },
            )


def test_calculate_order_rejects_unavailable_or_invalid_items():
    with SessionLocal() as db:
        with pytest.raises(ValueError, match='quantidade'):
            calculate_order(db, [{'id': 1, 'quantity': 21}])

        with pytest.raises(ValueError, match='dispon'):
            calculate_order(db, [{'id': 999999, 'quantity': 1}])


def test_order_status_normalization():
    assert normalize_order_status(' SHIPPED ') == 'shipped'

    with pytest.raises(Exception) as exc_info:
        normalize_order_status('inventado')
    assert getattr(exc_info.value, 'status_code', None) == 400


def test_update_infinitepay_payment_approves_and_rejects_safely():
    order = SimpleNamespace(total=149.90, payment_method='checkout', status='pending')
    payment = SimpleNamespace(
        order=order,
        provider='infinitepay',
        provider_order_id=None,
        provider_payment_id=None,
        method='checkout',
        status='pending',
        status_detail=None,
    )

    with pytest.raises(ValueError, match='Valor confirmado'):
        update_infinitepay_payment(payment, {'amount': cents(1), 'success': True, 'paid': True})

    assert update_infinitepay_payment(
        payment,
        {'amount': cents(order.total), 'success': False, 'paid': False},
    ) is False
    assert payment.status == 'pending'
    assert order.status == 'pending'

    assert update_infinitepay_payment(
        payment,
        {
            'amount': cents(order.total),
            'success': True,
            'paid': True,
            'slug': 'invoice-123',
            'transaction_nsu': 'transaction-123',
            'capture_method': 'pix',
        },
    ) is True
    assert payment.status == 'paid'
    assert payment.method == 'pix'
    assert payment.provider_order_id == 'invoice-123'
    assert payment.provider_payment_id == 'transaction-123'
    assert order.status == 'paid'
    assert order.payment_method == 'pix'


def test_public_url_uses_configured_base_url():
    request = SimpleNamespace(base_url='http://localhost:5000/')

    assert public_url(request, '/checkout') == 'https://vj.example.com/checkout'


def test_product_media_helpers_normalize_inputs():
    assert product_image_list({'images': [' img1.png ', '', 'img2.png']}) == [
        'img1.png',
        'img2.png',
    ]
    assert product_image_list({'image': 'img.png'}) == ['img.png']
    assert storage_slug('Anel Coracao N 2') == 'anel-coracao-n-2'
    assert normalize_stock_status(None) == 'available'
    assert normalize_stock_status('preorder') == 'preorder'

    with pytest.raises(Exception) as exc_info:
        normalize_stock_status('vendido')
    assert getattr(exc_info.value, 'status_code', None) == 400


def test_validation_helpers_normalize_and_reject_bad_customer_data():
    assert normalize_email(' CLIENTE@Example.COM ') == 'cliente@example.com'
    assert validate_cpf('123.456.789-09') == '12345678909'
    assert normalize_phone('+55 (11) 99999-9999') == '11999999999'
    assert clean_text(' <script>alert(1)</script> Cliente ') == 'alert(1) Cliente'

    with pytest.raises(ValueError, match='E-mail'):
        normalize_email('cliente@')
    with pytest.raises(ValueError, match='CPF'):
        validate_cpf('111.111.111-11')
    with pytest.raises(ValueError, match='Telefone'):
        normalize_phone('123')


def test_validate_image_bytes_checks_real_content_and_size():
    content_type, extension = validate_image_bytes(
        TINY_GIF,
        'image/gif',
        filename='produto.gif',
        max_bytes=1024,
    )

    assert content_type == 'image/gif'
    assert extension == '.gif'

    with pytest.raises(ValueError, match='imagem invalido'):
        validate_image_bytes(b'nao-e-imagem', 'image/png', filename='fake.png', max_bytes=1024)

    with pytest.raises(ValueError, match='maior'):
        validate_image_bytes(TINY_GIF, 'image/gif', filename='produto.gif', max_bytes=1)


def test_r2_upload_uses_s3_compatible_endpoint(monkeypatch):
    calls = []

    class FakeResponse:
        def raise_for_status(self):
            return None

    def fake_request(self, method, url, **kwargs):
        calls.append((method, url, kwargs, self.trust_env))
        return FakeResponse()

    monkeypatch.setenv('R2_ACCOUNT_ID', 'account123')
    monkeypatch.setenv('R2_BUCKET', 'vjsemijoias-dev')
    monkeypatch.setenv('R2_ACCESS_KEY_ID', 'access123')
    monkeypatch.setenv('R2_SECRET_ACCESS_KEY', 'secret123')
    monkeypatch.setenv('R2_PUBLIC_BASE_URL', 'https://assets-dev.example.com')
    monkeypatch.setattr('backend.services.storage.requests.Session.request', fake_request)

    result = upload_r2_object('catalog/admin/produto/img_1.gif', b'img', 'image/gif')

    assert result == 'https://assets-dev.example.com/catalog/admin/produto/img_1.gif'
    assert calls[0][0] == 'PUT'
    assert calls[0][1] == (
        'https://account123.r2.cloudflarestorage.com/'
        'vjsemijoias-dev/catalog/admin/produto/img_1.gif'
    )
    assert calls[0][2]['data'] == b'img'
    assert calls[0][2]['headers']['content-type'] == 'image/gif'
    assert calls[0][2]['headers']['authorization'].startswith('AWS4-HMAC-SHA256 ')
    assert calls[0][3] is False


def test_admin_image_upload_can_store_on_r2(monkeypatch):
    uploads = []
    product = SimpleNamespace(id=42, name='Colar R2')

    def fake_store(key, content, content_type):
        uploads.append((key, content, content_type))
        return f'https://assets-dev.example.com/{key}'

    monkeypatch.setenv('STORAGE_BACKEND', 'r2')
    monkeypatch.setattr('backend.services.product_media.store_public_file', fake_store)

    images = store_admin_gallery_images(
        product,
        ['data:image/gif;base64,R0lGODlhAQABAIAAAAAAAP///ywAAAAAAQABAAACAUwAOw=='],
    )

    assert images == ['https://assets-dev.example.com/catalog/admin/000042-colar-r2/img_1.gif']
    assert uploads[0][0] == 'catalog/admin/000042-colar-r2/img_1.gif'
    assert uploads[0][2] == 'image/gif'
