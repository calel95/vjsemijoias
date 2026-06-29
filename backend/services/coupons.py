from datetime import UTC, datetime, time
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from backend.models import Coupon, CouponRedemption, Order
from backend.services.validation import (
    clean_text,
    normalize_email,
    normalize_money_decimal,
    validate_cpf,
)


DISCOUNT_TYPES = {"percent", "fixed"}


def money(value):
    try:
        return Decimal(str(value)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    except (InvalidOperation, TypeError, ValueError) as exc:
        raise ValueError("Valor monetario invalido") from exc


def normalize_coupon_code(value, *, required=True) -> str:
    code = clean_text(value, field="codigo do cupom", max_length=20, required=required)
    code = code.upper().replace(" ", "")
    if required and not code:
        raise ValueError("Campo obrigatorio: codigo do cupom")
    if code and not all(char.isalnum() or char in {"-", "_"} for char in code):
        raise ValueError("Codigo do cupom deve usar letras, numeros, hifen ou underscore")
    return code


def normalize_int(value, *, field: str, minimum: int = 0) -> int:
    try:
        number = int(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{field} invalido") from exc
    if number < minimum:
        raise ValueError(f"{field} nao pode ser negativo")
    return number


def parse_coupon_datetime(value, *, end_of_day=False):
    if value in (None, ""):
        return None
    raw = str(value).strip()
    try:
        if len(raw) == 10:
            parsed_date = datetime.strptime(raw, "%Y-%m-%d").date()
            parsed = datetime.combine(
                parsed_date,
                time.max if end_of_day else time.min,
                tzinfo=UTC,
            )
        else:
            parsed = datetime.fromisoformat(raw.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError("Data do cupom invalida") from exc
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=UTC)
    return parsed.astimezone(UTC)


def normalize_coupon_payload(data, *, partial=False):
    payload = {}
    if not partial or "code" in data:
        payload["code"] = normalize_coupon_code(data.get("code"), required=not partial)

    if not partial or "discount_type" in data:
        discount_type = str(data.get("discount_type") or "percent").strip().lower()
        if discount_type not in DISCOUNT_TYPES:
            raise ValueError("Tipo de desconto deve ser percent ou fixed")
        payload["discount_type"] = discount_type

    if not partial or "discount_value" in data:
        discount_value = normalize_money_decimal(
            data.get("discount_value"),
            field="valor do desconto",
            minimum=Decimal("0.01"),
        )
        discount_type = payload.get("discount_type") or str(
            data.get("discount_type") or "percent"
        ).strip().lower()
        if discount_type == "percent" and discount_value > Decimal("100.00"):
            raise ValueError("Desconto percentual deve ser no maximo 100")
        payload["discount_value"] = discount_value

    if not partial or "minimum_subtotal" in data:
        payload["minimum_subtotal"] = normalize_money_decimal(
            data.get("minimum_subtotal", 0),
            field="valor minimo de compra",
            minimum=Decimal("0.00"),
        )

    if not partial or "usage_limit" in data:
        payload["usage_limit"] = normalize_int(
            data.get("usage_limit", 0),
            field="limite de uso",
        )

    if not partial or "per_customer_limit" in data:
        payload["per_customer_limit"] = normalize_int(
            data.get("per_customer_limit", 0),
            field="limite por cliente",
        )

    if not partial or "is_active" in data:
        payload["is_active"] = bool(data.get("is_active", True))

    if not partial or "starts_at" in data:
        payload["starts_at"] = parse_coupon_datetime(data.get("starts_at"))

    if not partial or "ends_at" in data:
        payload["ends_at"] = parse_coupon_datetime(data.get("ends_at"), end_of_day=True)

    starts_at = payload.get("starts_at")
    ends_at = payload.get("ends_at")
    if starts_at and ends_at and ends_at < starts_at:
        raise ValueError("Data final do cupom deve ser maior que a data inicial")
    return payload


def _aware(value):
    if value is None:
        return None
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


def calculate_coupon_discount(coupon: Coupon, subtotal) -> Decimal:
    subtotal = money(subtotal)
    discount_value = money(coupon.discount_value or coupon.discount_percent or 0)
    if coupon.discount_type == "fixed":
        return min(discount_value, subtotal).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    return (subtotal * discount_value / Decimal("100")).quantize(
        Decimal("0.01"), rounding=ROUND_HALF_UP
    )


def validate_coupon_for_order(
    db: Session,
    code,
    subtotal,
    *,
    customer_email: str = "",
    customer_cpf: str = "",
) -> tuple[Coupon, Decimal]:
    coupon_code = normalize_coupon_code(code)
    coupon = db.scalar(
        select(Coupon).where(Coupon.code == coupon_code, Coupon.is_active.is_(True))
    )
    if not coupon:
        raise ValueError("Cupom invalido ou expirado")

    now = datetime.now(UTC)
    starts_at = _aware(coupon.starts_at)
    ends_at = _aware(coupon.ends_at)
    if starts_at and now < starts_at:
        raise ValueError("Cupom ainda nao esta valido")
    if ends_at and now > ends_at:
        raise ValueError("Cupom expirado")

    subtotal = money(subtotal)
    minimum_subtotal = money(coupon.minimum_subtotal or 0)
    if subtotal < minimum_subtotal:
        raise ValueError(f"Cupom valido para compras acima de R$ {minimum_subtotal:.2f}")

    if coupon.usage_limit > 0 and coupon.used_count >= coupon.usage_limit:
        raise ValueError("Cupom esgotado")

    per_customer_limit = int(coupon.per_customer_limit or 0)
    if per_customer_limit > 0:
        email = normalize_email(customer_email, required=False)
        cpf = validate_cpf(customer_cpf, required=False)
        if email or cpf:
            filters = []
            if email:
                filters.append(CouponRedemption.customer_email == email)
            if cpf:
                filters.append(CouponRedemption.customer_cpf == cpf)
            used_by_customer = db.scalar(
                select(func.count(CouponRedemption.id)).where(
                    CouponRedemption.coupon_id == coupon.id,
                    or_(*filters),
                )
            ) or 0
            if used_by_customer >= per_customer_limit:
                raise ValueError("Cupom ja utilizado por este cliente")

    return coupon, calculate_coupon_discount(coupon, subtotal)


def redeem_coupon(
    db: Session,
    *,
    coupon: Coupon,
    order: Order,
    discount_amount,
    customer_email: str = "",
    customer_cpf: str = "",
):
    redemption = CouponRedemption(
        coupon=coupon,
        order=order,
        customer_email=normalize_email(customer_email, required=False),
        customer_cpf=validate_cpf(customer_cpf, required=False),
        discount_amount=money(discount_amount),
    )
    coupon.used_count = int(coupon.used_count or 0) + 1
    db.add(redemption)
    return redemption
