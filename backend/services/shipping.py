from decimal import Decimal

from sqlalchemy.orm import Session

from backend.services.validation import digits_only, normalize_money_decimal
from backend.store_config import effective_store_settings


INTERNAL_PROVIDER = "internal"


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

    option = {
        "id": mode,
        "provider": INTERNAL_PROVIDER,
        "service": service,
        "shipping": shipping,
        "message": _shipping_message(mode, shipping, free_minimum),
        "estimated_days": active_settings.shipping.estimated_days,
        "destination_zip": destination_zip,
        "package": package,
    }
    return [option]


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
