from decimal import Decimal, ROUND_HALF_UP

from fastapi import Request

from backend.config import settings
from backend.infinitepay_client import InfinitePayClient
from backend.services.orders import money


def infinitepay():
    return InfinitePayClient(settings.infinitepay_handle, settings.infinitepay_api_base)


def public_url(request: Request, path):
    base = settings.public_base_url or str(request.base_url).rstrip("/")
    return f"{base}/{path.lstrip('/')}"


def cents(value):
    return int((money(value) * 100).quantize(Decimal("1"), rounding=ROUND_HALF_UP))


def update_infinitepay_payment(payment, provider_data):
    if int(provider_data.get("amount") or 0) != cents(payment.order.total):
        raise ValueError("Valor confirmado pela InfinitePay não corresponde ao pedido")
    if not provider_data.get("success") or not provider_data.get("paid"):
        return False
    payment.provider = "infinitepay"
    payment.provider_order_id = (
        provider_data.get("slug")
        or provider_data.get("invoice_slug")
        or payment.provider_order_id
    )
    payment.provider_payment_id = (
        provider_data.get("transaction_nsu") or payment.provider_payment_id
    )
    payment.method = provider_data.get("capture_method") or payment.method
    payment.status = "paid"
    payment.status_detail = "approved"
    payment.order.payment_method = payment.method
    payment.order.status = "paid"
    return True
