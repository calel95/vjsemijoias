from typing import Any

from backend.services.product_media import normalize_stock_status
from backend.services.product_shipping import (
    normalize_dimension_cm,
    normalize_shipping_profile,
    normalize_weight_grams,
)
from backend.services.stock import (
    normalize_low_stock_alert,
    normalize_sku,
    normalize_stock_quantity,
)
from backend.services.validation import (
    clean_text,
    clean_text_list,
    normalize_money_decimal,
    normalize_product_reference,
)


def normalize_product_payload(data: dict[str, Any], *, partial=False):
    cleaned: dict[str, Any] = {}
    text_fields = {
        "name": (200, True),
        "category": (50, True),
        "categoryName": (50, False),
        "icon": (10, False),
        "badge": (20, False),
        "description": (1000, True),
    }
    for field, (max_length, required_on_create) in text_fields.items():
        if field in data or (required_on_create and not partial):
            cleaned[field] = clean_text(
                data.get(field),
                field=field,
                max_length=max_length,
                required=required_on_create and not partial,
            )

    if "categoryName" not in cleaned and "category" in cleaned:
        cleaned["categoryName"] = cleaned["category"].capitalize()
    if "price" in data or not partial:
        cleaned["price"] = normalize_money_decimal(data.get("price"), field="price")
    if "oldPrice" in data:
        cleaned["oldPrice"] = normalize_money_decimal(
            data.get("oldPrice"),
            field="oldPrice",
            required=False,
        )
    if "sku" in data:
        cleaned["sku"] = normalize_sku(data.get("sku"))
    if "reference" in data:
        cleaned["reference"] = normalize_product_reference(data.get("reference"))
    if "stock_quantity" in data:
        cleaned["stock_quantity"] = normalize_stock_quantity(data.get("stock_quantity"))
    elif not partial:
        cleaned["stock_quantity"] = 0
    if "low_stock_alert" in data:
        cleaned["low_stock_alert"] = normalize_low_stock_alert(data.get("low_stock_alert"))
    elif not partial:
        cleaned["low_stock_alert"] = 1
    if "weight_grams" in data:
        cleaned["weight_grams"] = normalize_weight_grams(data.get("weight_grams"))
    elif not partial:
        cleaned["weight_grams"] = normalize_weight_grams(None)
    for field in ["height_cm", "width_cm", "length_cm"]:
        if field in data:
            cleaned[field] = normalize_dimension_cm(data.get(field), field=field)
        elif not partial:
            cleaned[field] = normalize_dimension_cm(None, field=field)
    if "shipping_profile" in data:
        cleaned["shipping_profile"] = normalize_shipping_profile(data.get("shipping_profile"))
    elif not partial:
        cleaned["shipping_profile"] = normalize_shipping_profile(None)
    if "features" in data:
        cleaned["features"] = clean_text_list(data.get("features"), field="features")
    return cleaned