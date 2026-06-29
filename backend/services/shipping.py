import logging
import re
import unicodedata
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


def internal_shipping_option(
    subtotal,
    *,
    zip_code: str,
    package: dict | None,
    db: Session | None,
    active_settings=None,
):
    subtotal = money(subtotal)
    destination_zip = normalize_zip(zip_code)
    active_settings = active_settings or effective_store_settings(db)
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
        if subtotal >= free_minimum:
            shipping = Decimal("0.00")
            service = "Frete gratis"
        elif fixed_value > Decimal("0.00"):
            shipping = fixed_value
            service = "Frete fixo"
        else:
            raise ValueError(
                "Configure um frete fixo maior que zero para pedidos abaixo do minimo de frete gratis"
            )
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


def store_free_shipping_should_apply(active_settings, subtotal) -> bool:
    mode = active_settings.shipping.mode
    if mode == "free":
        return True
    if mode != "threshold":
        return False
    return money(subtotal) >= money(active_settings.shipping.free_minimum)


def threshold_missing_fallback_price(active_settings, subtotal) -> bool:
    return (
        active_settings.shipping.mode == "threshold"
        and money(subtotal) < money(active_settings.shipping.free_minimum)
        and money(active_settings.shipping.fixed_value) == Decimal("0.00")
    )

def store_free_shipping_applies(internal_option: dict) -> bool:
    return (
        internal_option.get("shipping") == Decimal("0.00")
        and str(internal_option.get("service") or "").lower() == "frete gratis"
    )


def apply_store_free_shipping(options: list[dict], free_option: dict) -> list[dict]:
    free_options = []
    for option in options:
        free_options.append(
            {
                **option,
                "shipping": Decimal("0.00"),
                "message": free_option["message"],
                "free_shipping_applied": True,
            }
        )
    return free_options

def melhor_envio_payload(
    subtotal,
    destination_zip: str,
    package: dict,
    *,
    from_postal_code: str = "",
    services: str | None = None,
):
    from_zip = normalize_zip(from_postal_code or settings.melhor_envio_from_postal_code)
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
    service_filter = str(settings.melhor_envio_services if services is None else services).strip()
    if service_filter:
        payload["services"] = service_filter
    return payload


def allowed_company_ids(raw_ids: str | None = None):
    raw_ids = settings.melhor_envio_allowed_company_ids if raw_ids is None else raw_ids
    if not raw_ids:
        return set()
    try:
        return {int(item.strip()) for item in raw_ids.split(",") if item.strip()}
    except ValueError as exc:
        raise ValueError("MELHOR_ENVIO_ALLOWED_COMPANY_IDS deve conter apenas numeros separados por virgula") from exc

def normalize_shipping_name(value) -> str:
    normalized = unicodedata.normalize("NFKD", str(value or "")).encode("ascii", "ignore").decode("ascii")
    return re.sub(r"[^a-z0-9]+", " ", normalized.lower()).strip()


def shipping_display_service(option: dict) -> str:
    company = str(option.get("company") or "").strip()
    service = str(option.get("service") or "").strip()
    company_key = normalize_shipping_name(company)
    service_key = normalize_shipping_name(service)

    if company_key == "correios":
        if "sedex" in service_key:
            return "SEDEX"
        if "pac" in service_key:
            return "PAC"
        return service or company or "Correios"

    if company:
        return company
    return service or "Frete"


def shipping_group_key(option: dict) -> tuple[str, str]:
    company = normalize_shipping_name(option.get("company") or "")
    service = normalize_shipping_name(option.get("service") or "")
    carrier = company or service or str(option.get("provider") or "frete")

    if carrier == "correios":
        if "sedex" in service:
            return (carrier, "sedex")
        if "pac" in service:
            return (carrier, "pac")
        return (carrier, service or "correios")

    return (carrier, "default")


def shipping_delivery_days(option: dict) -> int:
    match = re.search(r"\d+", str(option.get("estimated_days") or ""))
    return int(match.group(0)) if match else 9999


def professionalize_shipping_options(options: list[dict]) -> list[dict]:
    grouped: dict[tuple[str, str], dict] = {}
    for option in options:
        display_service = shipping_display_service(option)
        professional = {
            **option,
            "service": display_service,
            "display_service": display_service,
        }
        professional["message"] = f"{display_service}: R$ {professional['shipping']:.2f}"
        key = shipping_group_key(professional)
        current = grouped.get(key)
        if current is None or (
            professional["shipping"],
            shipping_delivery_days(professional),
            str(professional.get("id") or ""),
        ) < (
            current["shipping"],
            shipping_delivery_days(current),
            str(current.get("id") or ""),
        ):
            grouped[key] = professional
    return sorted(grouped.values(), key=lambda option: (option["shipping"], shipping_delivery_days(option)))


def parse_melhor_envio_options(
    data,
    *,
    destination_zip: str,
    package: dict,
    allowed_company_ids_raw: str | None = None,
):
    if not isinstance(data, list):
        raise ValueError("Resposta invalida do Melhor Envio")

    allowed_companies = allowed_company_ids(allowed_company_ids_raw)
    options = []
    for item in data:
        if not isinstance(item, dict) or item.get("error"):
            continue
        price = item.get("custom_price") or item.get("price")
        if price in (None, ""):
            continue
        service_id = str(item.get("id") or item.get("service_id") or "")
        company = item.get("company") if isinstance(item.get("company"), dict) else {}
        company_id = company.get("id")
        if allowed_companies and company_id not in allowed_companies:
            continue
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
                "company_id": company_id,
                "company": company.get("name"),
                "raw_service_id": service_id,
            }
        )
    if not options:
        raise ValueError("Nenhuma opcao valida retornada pelo Melhor Envio")
    return professionalize_shipping_options(options)


def melhor_envio_timeout(value) -> float:
    try:
        return float(value or settings.melhor_envio_timeout_seconds)
    except (TypeError, ValueError):
        return settings.melhor_envio_timeout_seconds


def fetch_melhor_envio_options(subtotal, *, destination_zip: str, package: dict, shipping_settings=None):
    from_postal_code = (
        getattr(shipping_settings, "melhor_envio_from_postal_code", "")
        or settings.melhor_envio_from_postal_code
    )
    services = getattr(shipping_settings, "melhor_envio_services", "") if shipping_settings else ""
    allowed_companies = (
        getattr(shipping_settings, "melhor_envio_allowed_company_ids", "")
        if shipping_settings
        else None
    )
    timeout_seconds = melhor_envio_timeout(
        getattr(shipping_settings, "melhor_envio_timeout_seconds", "")
        if shipping_settings
        else None
    )

    if not settings.melhor_envio_token:
        raise ValueError("MELHOR_ENVIO_TOKEN nao configurado")
    if not from_postal_code:
        raise ValueError("MELHOR_ENVIO_FROM_POSTAL_CODE nao configurado")

    session = requests.Session()
    session.trust_env = False
    response = session.post(
        f"{settings.melhor_envio_api_base}/me/shipment/calculate",
        json=melhor_envio_payload(
            subtotal,
            destination_zip,
            package,
            from_postal_code=from_postal_code,
            services=services,
        ),
        headers={
            "Accept": "application/json",
            "Content-Type": "application/json",
            "Authorization": f"Bearer {settings.melhor_envio_token}",
            "User-Agent": "vjsemijoias/1.0",
        },
        timeout=timeout_seconds,
    )
    response.raise_for_status()
    return parse_melhor_envio_options(
        response.json(),
        destination_zip=destination_zip,
        package=package,
        allowed_company_ids_raw=allowed_companies,
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
    active_settings = effective_store_settings(db)
    provider = active_settings.shipping.provider

    if provider == MELHOR_ENVIO_PROVIDER and destination_zip and package:
        try:
            provider_options = fetch_melhor_envio_options(
                subtotal,
                destination_zip=destination_zip,
                package=package,
                shipping_settings=active_settings.shipping,
            )
            if store_free_shipping_should_apply(active_settings, subtotal):
                free_option = internal_shipping_option(
                    subtotal,
                    zip_code=destination_zip,
                    package=package,
                    db=db,
                    active_settings=active_settings,
                )
                return apply_store_free_shipping(provider_options, free_option)
            return provider_options
        except (requests.RequestException, ValueError) as exc:
            if threshold_missing_fallback_price(active_settings, subtotal):
                logger.warning("Falha ao calcular frete pago no Melhor Envio sem fallback configurado: %s", exc)
                raise ValueError(
                    "Nao foi possivel calcular o frete pago. Configure um frete fixo de fallback ou revise a integracao de frete"
                ) from exc
            internal_option = internal_shipping_option(
                subtotal,
                zip_code=destination_zip,
                package=package,
                db=db,
                active_settings=active_settings,
            )
            internal_option["fallback_reason"] = "melhor_envio_unavailable"
            logger.warning("Falha ao calcular frete no Melhor Envio: %s", exc)
            return [internal_option]

    internal_option = internal_shipping_option(
        subtotal,
        zip_code=destination_zip,
        package=package,
        db=db,
        active_settings=active_settings,
    )
    if provider == INTERNAL_PROVIDER:
        return [internal_option]
    if provider != MELHOR_ENVIO_PROVIDER:
        internal_option["fallback_reason"] = "shipping_provider_unknown"
        logger.warning("SHIPPING_PROVIDER desconhecido: %s", provider)
        return [internal_option]
    internal_option["fallback_reason"] = "melhor_envio_requires_zip_and_package"
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