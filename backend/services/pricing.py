from decimal import Decimal, InvalidOperation, ROUND_HALF_UP

MONEY_QUANT = Decimal("0.01")
RATIO_QUANT = Decimal("0.0001")
DEFAULT_MARKUP = Decimal("2.00")
DEFAULT_PACKAGING_COST = Decimal("9.34")

PAYMENT_FEES = {
    "preco_pix": Decimal("0.00"),
    "preco_debito": Decimal("1.37"),
    "preco_credito_vista": Decimal("3.15"),
    "preco_credito_2x": Decimal("5.39"),
    "preco_credito_3x": Decimal("6.12"),
    "preco_credito_4x": Decimal("6.85"),
    "preco_credito_5x": Decimal("7.57"),
    "preco_credito_6x": Decimal("8.28"),
    "preco_credito_7x": Decimal("8.99"),
    "preco_credito_8x": Decimal("9.69"),
    "preco_credito_9x": Decimal("10.38"),
    "preco_credito_10x": Decimal("11.06"),
    "preco_credito_11x": Decimal("11.74"),
    "preco_credito_12x": Decimal("12.40"),
}

CALCULATED_PRICE_FIELDS = tuple(PAYMENT_FEES.keys()) + (
    "custo_total",
    "lucro_pix",
    "margem_pix",
)


def money(value, *, field="valor", required=True, default=None, minimum=Decimal("0.00")):
    if value in (None, ""):
        if default is not None:
            value = default
        elif required:
            raise ValueError(f"Campo obrigatorio: {field}")
        else:
            return None
    try:
        number = Decimal(str(value)).quantize(MONEY_QUANT, rounding=ROUND_HALF_UP)
    except (InvalidOperation, TypeError, ValueError) as exc:
        raise ValueError(f"{field} invalido") from exc
    if number < Decimal(str(minimum)):
        raise ValueError(f"{field} nao pode ser negativo")
    return number


def ratio(value, *, field="markup", default=DEFAULT_MARKUP):
    if value in (None, ""):
        value = default
    try:
        number = Decimal(str(value)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    except (InvalidOperation, TypeError, ValueError) as exc:
        raise ValueError(f"{field} invalido") from exc
    if number <= 0:
        raise ValueError(f"{field} deve ser maior que zero")
    return number


def calculate_pricing(custo_peca, custo_embalagem=None, markup=None):
    cost_piece = money(custo_peca, field="custo_peca")
    packaging = money(
        custo_embalagem,
        field="custo_embalagem",
        default=DEFAULT_PACKAGING_COST,
    )
    markup_value = ratio(markup)
    total_cost = (cost_piece + packaging).quantize(MONEY_QUANT, rounding=ROUND_HALF_UP)

    result = {
        "custo_peca": cost_piece,
        "custo_embalagem": packaging,
        "custo_total": total_cost,
        "markup": markup_value,
    }
    for field, fee in PAYMENT_FEES.items():
        denominator = Decimal("1.00") - (fee / Decimal("100"))
        result[field] = (total_cost * markup_value / denominator).quantize(
            MONEY_QUANT,
            rounding=ROUND_HALF_UP,
        )

    pix_price = result["preco_pix"]
    pix_fee = PAYMENT_FEES["preco_pix"]
    profit = (pix_price - total_cost - (pix_price * pix_fee / Decimal("100"))).quantize(
        MONEY_QUANT,
        rounding=ROUND_HALF_UP,
    )
    result["lucro_pix"] = profit
    result["margem_pix"] = (
        (profit / pix_price).quantize(RATIO_QUANT, rounding=ROUND_HALF_UP)
        if pix_price
        else Decimal("0.0000")
    )
    return result


def apply_pricing(product, *, custo_peca, custo_embalagem=None, markup=None):
    values = calculate_pricing(custo_peca, custo_embalagem, markup)
    for field, value in values.items():
        setattr(product, field, value)
    product.price = values["preco_pix"]
    return values
