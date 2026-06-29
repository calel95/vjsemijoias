from decimal import Decimal

from backend.services.validation import clean_text, normalize_money_decimal


DEFAULT_WEIGHT_GRAMS = 100
DEFAULT_HEIGHT_CM = Decimal("2.00")
DEFAULT_WIDTH_CM = Decimal("10.00")
DEFAULT_LENGTH_CM = Decimal("15.00")
DEFAULT_SHIPPING_PROFILE = "default"


def normalize_weight_grams(value, *, required=False) -> int:
    if value in (None, ""):
        if required:
            raise ValueError("Peso obrigatorio")
        return DEFAULT_WEIGHT_GRAMS
    try:
        weight = int(value)
    except (TypeError, ValueError) as exc:
        raise ValueError("Peso deve ser um numero inteiro em gramas") from exc
    if weight < 1 or weight > 30000:
        raise ValueError("Peso deve ficar entre 1g e 30000g")
    return weight


def normalize_dimension_cm(value, *, field: str, required=False) -> Decimal:
    if value in (None, ""):
        if required:
            raise ValueError(f"{field} obrigatorio")
        defaults = {
            "height_cm": DEFAULT_HEIGHT_CM,
            "width_cm": DEFAULT_WIDTH_CM,
            "length_cm": DEFAULT_LENGTH_CM,
        }
        return defaults[field]
    number = normalize_money_decimal(value, field=field, minimum=Decimal("0.01"))
    if number > Decimal("200.00"):
        raise ValueError(f"{field} deve ficar entre 0.01cm e 200cm")
    return number


def normalize_shipping_profile(value) -> str:
    profile = clean_text(
        value or DEFAULT_SHIPPING_PROFILE,
        field="shipping_profile",
        max_length=50,
    ).lower()
    return profile or DEFAULT_SHIPPING_PROFILE
