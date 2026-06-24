import logging
from decimal import Decimal

import requests
from sqlalchemy.orm import Session

from backend.config import settings
from backend.services.validation import digits_only, normalize_money_decimal
from backend.store_config import effective_store_settings


logger = logging.getLogger(__name__)
INTERNAL_PROVIDER = "internal"
MELHOR_ENVIO_PROVIDER = "melhor_envio"


def money(value):
    return normalize_money_decimal(value, field="valor")


def normalize_zip(value) -> str:
    raw_value = str(value or "").strip()
    zip_code = digits_only(value)
    if not raw_value:
        return ""
    if len(zip_code) != 8:
        raise ValueError("CEP deve conter 8 digitos")
    return zip_code


def _shipping_message(mode: str, shipping: Decimal, free_minimum: Decimal) -> str:
    if mode == "free":
        return "Frete Gratis!"
    if mode == "threshold" and shipping == Decimal("0.00"):
        return f"Frete gratis acima de R$ {free_minimum:.2f}"
    return f"Frete fixo de R$ {shipping:.2f}"


def _dimension(value, fallback: Decimal) -> Decimal:
    if value in (None, ""):
        return fallback
    return Decimal(str(value)).quantize(Decimal("0.01"))


def build_shipping_package(product_quantities):
    items = list(product_quantities)
    if not items:
        return None

    total_quantity = 0
    total_weight = 0
    max_length = Decimal("0.00")
    max_width = Decimal("0.00")
    stacked_height = Decimal("0.00")
    profiles = set()

    for product, quantity in items:
        quantity = int(quantity)
        if quantity < 1:
            raise ValueError("Quantidade invalida para calculo de frete")
        total_quantity += quantity
        total_weight += int(product.weight_grams or 100) * quantity
        max_length = max(max_length, _dimension(product.length_cm, Decimal("15.00")))
        max_width = max(max_width, _dimension(product.width_cm, Decimal("10.00")))
        stacked_height += _dimension(product.height_cm, Decimal("2.00")) * quantity
        profiles.add(product.shipping_profile or "default")

    return {
        "item_count": total_quantity,
        "weight_grams": total_weight,
        "height_cm": stacked_height,
        "width_cm": max_width,
        "length_cm": max_length,
        "shipping_profile": profiles.pop() if len(profiles) == 1 else "mixed",
    }


def internal_shipping_option(subtotal, *, zip_code: str, package: dict | None, db: Session | None):
    subtotal = money(subtotal)
    destination_zip = normalize_zip(zip_code)
    active_settings = effective_store_settings(db)
    mode = active_settings.shipping.mode
    fixed_value = money(active_settings.shipping.fixed_value)
    free_minimum = money(active_settings.shipping.free_minimum)

    if mode == "free":
        shipping = Decimal("0.00")
        service = "Frete gratis"
    elif mode == "fixed":
        shipping = fixed_value
        service = "Frete fixo"
    elif mode == "threshold":
        shipping = Decimal("0.00") if subtotal >= free_minimum else fixed_value
        service = "Frete gratis" if shipping == Decimal("0.00") else "Frete fixo"
    else:
        raise ValueError("SHIPPING_MODE deve ser free, fixed ou threshold")

    return {
        "id": mode,
        "provider": INTERNAL_PROVIDER,
        "service": service,
        "shipping": shipping,
        "message": _shipping_message(mode, shipping, free_minimum),
        "estimated_days": active_settings.shipping.estimated_days,
        "destination_zip": destination_zip,
        "package": package,
    }


def melhor_envio_payload(subtotal, destination_zip: str, package: dict):
    from_zip = normalize_zip(settings.melhor_envio_from_postal_code)
    weight_kg = max(Decimal(package["weight_grams"]) / Decimal("1000"), Decimal("0.01"))
    product = {
        "id": package.get("shipping_profile") or "default",
        "width": float(package["width_cm"]),
        "height": float(package["height_cm"]),
        "length": float(package["length_cm"]),
        "weight": float(weight_kg.quantize(Decimal("0.001"))),
        "insurance_value": float(money(subtotal)),
        "quantity": 1,
    }
    payload = {
        "from": {"postal_code": from_zip},
        "to": {"postal_code": destination_zip},
        "products": [product],
        "options": {
            "receipt": False,
            "own_hand": False,
            "collect": False,
        },
    }
    if settings.melhor_envio_services:
        payload["services"] = settings.melhor_envio_services
    return payload


def parse_melhor_envio_options(data, *, destination_zip: str, package: dict):
    if not isinstance(data, list):
        raise ValueError("Resposta invalida do Melhor Envio")

    options = []
    for item in data:
        if not isinstance(item, dict) or item.get("error"):
            continue
        price = item.get("custom_price") or item.get("price")
        if price in (None, ""):
            continue
        service_id = str(item.get("id") or item.get("service_id") or "")
        company = item.get("company") if isinstance(item.get("company"), dict) else {}
        service = item.get("name") or company.get("name") or f"Servico {service_id}".strip()
        estimated_days = item.get("custom_delivery_time") or item.get("delivery_time") or ""
        shipping = money(price)
        options.append(
            {
                "id": f"melhor_envio:{service_id}" if service_id else "melhor_envio",
                "provider": MELHOR_ENVIO_PROVIDER,
                "service": str(service),
                "shipping": shipping,
                "message": f"{service}: R$ {shipping:.2f}",
                "estimated_days": str(estimated_days),
                "destination_zip": destination_zip,
                "package": package,
                "raw_service_id": service_id,
            }
        )
    if not options:
        raise ValueError("Nenhuma opcao valida retornada pelo Melhor Envio")
    return sorted(options, key=lambda option: option["shipping"])


def fetch_melhor_envio_options(subtotal, *, destination_zip: str, package: dict):
    if not settings.melhor_envio_token:
        raise ValueError("MELHOR_ENVIO_TOKEN nao configurado")
    if not settings.melhor_envio_from_postal_code:
        raise ValueError("MELHOR_ENVIO_FROM_POSTAL_CODE nao configurado")

    session = requests.Session()
    session.trust_env = False
    response = session.post(
        f"{settings.melhor_envio_api_base}/me/shipment/calculate",
        json=melhor_envio_payload(subtotal, destination_zip, package),
        headers={
            "Accept": "application/json",
            "Content-Type": "application/json",
            "Authorization": f"Bearer {settings.melhor_envio_token}",
            "User-Agent": "vjsemijoias/1.0",
        },
        timeout=settings.melhor_envio_timeout_seconds,
    )
    response.raise_for_status()
    return parse_melhor_envio_options(
        response.json(),
        destination_zip=destination_zip,
        package=package,
    )


def calculate_shipping_options(
    subtotal,
    *,
    zip_code: str = "",
    package: dict | None = None,
    db: Session | None = None,
):
    subtotal = money(subtotal)
    destination_zip = normalize_zip(zip_code)
    internal_option = internal_shipping_option(
        subtotal,
        zip_code=destination_zip,
        package=package,
        db=db,
    )

    provider = settings.shipping_provider
    if provider == INTERNAL_PROVIDER:
        return [internal_option]
    if provider != MELHOR_ENVIO_PROVIDER:
        internal_option["fallback_reason"] = "shipping_provider_unknown"
        logger.warning("SHIPPING_PROVIDER desconhecido: %s", provider)
        return [internal_option]
    if not destination_zip or not package:
        internal_option["fallback_reason"] = "melhor_envio_requires_zip_and_package"
        return [internal_option]

    try:
        return fetch_melhor_envio_options(subtotal, destination_zip=destination_zip, package=package)
    except (requests.RequestException, ValueError) as exc:
        internal_option["fallback_reason"] = "melhor_envio_unavailable"
        logger.warning("Falha ao calcular frete no Melhor Envio: %s", exc)
        return [internal_option]


def calculate_shipping(
    subtotal,
    *,
    zip_code: str = "",
    package: dict | None = None,
    db: Session | None = None,
):
    return calculate_shipping_options(subtotal, zip_code=zip_code, package=package, db=db)[0]


def serialize_shipping_package(package: dict | None):
    if not package:
        return None
    return {
        **package,
        "height_cm": float(package["height_cm"]),
        "width_cm": float(package["width_cm"]),
        "length_cm": float(package["length_cm"]),
    }


def serialize_shipping_option(option: dict):
    return {
        **option,
        "shipping": float(option["shipping"]),
        "package": serialize_shipping_package(option.get("package")),
    }