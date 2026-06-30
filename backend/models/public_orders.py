from __future__ import annotations

import json
from datetime import UTC, datetime
from decimal import Decimal

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base, MONEY_COLUMN, PERCENT_COLUMN, decimal_to_float, utc_now


class Order(Base):
    __tablename__ = "orders"

    id: Mapped[str] = mapped_column(String(50), primary_key=True)
    user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    customer_name: Mapped[str] = mapped_column(String(200))
    customer_email: Mapped[str] = mapped_column(String(200))
    customer_cpf: Mapped[str] = mapped_column(String(20))
    customer_phone: Mapped[str | None] = mapped_column(String(30), nullable=True)
    address_zip: Mapped[str | None] = mapped_column(String(20), nullable=True)
    address_street: Mapped[str | None] = mapped_column(String(200), nullable=True)
    address_number: Mapped[str | None] = mapped_column(String(20), nullable=True)
    address_complement: Mapped[str | None] = mapped_column(String(200), nullable=True)
    address_neighborhood: Mapped[str | None] = mapped_column(String(100), nullable=True)
    address_city: Mapped[str | None] = mapped_column(String(100), nullable=True)
    address_state: Mapped[str | None] = mapped_column(String(10), nullable=True)
    items: Mapped[str] = mapped_column(Text)
    subtotal: Mapped[Decimal] = mapped_column(MONEY_COLUMN)
    shipping: Mapped[Decimal] = mapped_column(MONEY_COLUMN, default=Decimal("0.00"))
    shipping_provider: Mapped[str | None] = mapped_column(String(50), nullable=True)
    shipping_service: Mapped[str | None] = mapped_column(String(100), nullable=True)
    shipping_estimated_days: Mapped[str | None] = mapped_column(String(50), nullable=True)
    shipping_destination_zip: Mapped[str | None] = mapped_column(String(20), nullable=True)
    shipping_option_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    shipping_company_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    shipping_company: Mapped[str | None] = mapped_column(String(100), nullable=True)
    discount: Mapped[Decimal] = mapped_column(MONEY_COLUMN, default=Decimal("0.00"))
    total: Mapped[Decimal] = mapped_column(MONEY_COLUMN)
    payment_method: Mapped[str | None] = mapped_column(String(50), nullable=True)
    status: Mapped[str] = mapped_column(String(50), default="pending")
    coupon: Mapped[str | None] = mapped_column(String(20), nullable=True)
    stock_deducted: Mapped[bool] = mapped_column(Boolean, default=False)
    idempotency_key: Mapped[str | None] = mapped_column(String(100), unique=True, nullable=True)
    public_token: Mapped[str | None] = mapped_column(String(100), unique=True, nullable=True)
    tracking_code: Mapped[str | None] = mapped_column(String(100), nullable=True)
    tracking_carrier: Mapped[str | None] = mapped_column(String(100), nullable=True)
    shipped_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    delivered_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    payment: Mapped["Payment | None"] = relationship(back_populates="order", uselist=False)
    events: Mapped[list["OrderEvent"]] = relationship(
        back_populates="order",
        cascade="all, delete-orphan",
        order_by="OrderEvent.created_at",
    )
    coupon_redemptions: Mapped[list["CouponRedemption"]] = relationship(
        back_populates="order",
        cascade="all, delete-orphan",
    )

    def to_dict(self):
        return {
            "id": self.id,
            "user_id": self.user_id,
            "customer_name": self.customer_name,
            "customer_email": self.customer_email,
            "customer_cpf": self.customer_cpf,
            "customer_phone": self.customer_phone,
            "address_zip": self.address_zip,
            "address_street": self.address_street,
            "address_number": self.address_number,
            "address_complement": self.address_complement,
            "address_neighborhood": self.address_neighborhood,
            "address_city": self.address_city,
            "address_state": self.address_state,
            "items": json.loads(self.items) if self.items else [],
            "subtotal": decimal_to_float(self.subtotal),
            "shipping": decimal_to_float(self.shipping),
            "shipping_provider": self.shipping_provider,
            "shipping_service": self.shipping_service,
            "shipping_estimated_days": self.shipping_estimated_days,
            "shipping_destination_zip": self.shipping_destination_zip,
            "shipping_option_id": self.shipping_option_id,
            "shipping_company_id": self.shipping_company_id,
            "shipping_company": self.shipping_company,
            "discount": decimal_to_float(self.discount),
            "total": decimal_to_float(self.total),
            "payment_method": self.payment_method,
            "status": self.status,
            "coupon": self.coupon,
            "stock_deducted": self.stock_deducted,
            "public_token": self.public_token,
            "tracking_code": self.tracking_code,
            "tracking_carrier": self.tracking_carrier,
            "shipped_at": self.shipped_at.isoformat() if self.shipped_at else None,
            "delivered_at": self.delivered_at.isoformat() if self.delivered_at else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "events": [event.to_dict() for event in self.events],
        }


class OrderEvent(Base):
    __tablename__ = "order_events"

    id: Mapped[int] = mapped_column(primary_key=True)
    order_id: Mapped[str] = mapped_column(ForeignKey("orders.id"), index=True)
    event_type: Mapped[str] = mapped_column(String(80))
    status: Mapped[str | None] = mapped_column(String(50), nullable=True)
    message: Mapped[str] = mapped_column(String(255))
    actor_user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    metadata_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, index=True
    )
    order: Mapped[Order] = relationship(back_populates="events")
    actor_user: Mapped[User | None] = relationship()

    def to_dict(self):
        try:
            metadata = json.loads(self.metadata_json) if self.metadata_json else {}
        except (TypeError, json.JSONDecodeError):
            metadata = {}
        return {
            "id": self.id,
            "order_id": self.order_id,
            "event_type": self.event_type,
            "status": self.status,
            "message": self.message,
            "actor_user_id": self.actor_user_id,
            "metadata": metadata,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }

class Newsletter(Base):
    __tablename__ = "newsletters"

    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(200), unique=True)
    coupon: Mapped[str] = mapped_column(String(20), default="VJ10")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)


class Coupon(Base):
    __tablename__ = "coupons"

    id: Mapped[int] = mapped_column(primary_key=True)
    code: Mapped[str] = mapped_column(String(20), unique=True)
    discount_percent: Mapped[Decimal] = mapped_column(
        PERCENT_COLUMN,
        default=Decimal("10.00"),
    )
    discount_type: Mapped[str] = mapped_column(String(20), default="percent")
    discount_value: Mapped[Decimal] = mapped_column(MONEY_COLUMN, default=Decimal("10.00"))
    minimum_subtotal: Mapped[Decimal] = mapped_column(MONEY_COLUMN, default=Decimal("0.00"))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    usage_limit: Mapped[int] = mapped_column(Integer, default=100)
    used_count: Mapped[int] = mapped_column(Integer, default=0)
    per_customer_limit: Mapped[int] = mapped_column(Integer, default=0)
    starts_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    ends_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, onupdate=utc_now
    )
    redemptions: Mapped[list["CouponRedemption"]] = relationship(
        back_populates="coupon",
        cascade="all, delete-orphan",
        order_by="CouponRedemption.created_at",
    )

    def to_dict(self, include_redemptions: bool = False):
        data = {
            "id": self.id,
            "code": self.code,
            "discount_percent": decimal_to_float(self.discount_percent),
            "discount_type": self.discount_type,
            "discount_value": decimal_to_float(self.discount_value),
            "minimum_subtotal": decimal_to_float(self.minimum_subtotal),
            "is_active": self.is_active,
            "usage_limit": self.usage_limit,
            "used_count": self.used_count,
            "per_customer_limit": self.per_customer_limit,
            "starts_at": self.starts_at.isoformat() if self.starts_at else None,
            "ends_at": self.ends_at.isoformat() if self.ends_at else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
        if include_redemptions:
            data["redemptions"] = [
                redemption.to_dict()
                for redemption in sorted(
                    self.redemptions,
                    key=lambda item: item.created_at or datetime.min.replace(tzinfo=UTC),
                    reverse=True,
                )[:20]
            ]
        return data


class CouponRedemption(Base):
    __tablename__ = "coupon_redemptions"
    __table_args__ = (UniqueConstraint("order_id"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    coupon_id: Mapped[int] = mapped_column(ForeignKey("coupons.id"), index=True)
    order_id: Mapped[str] = mapped_column(ForeignKey("orders.id"), index=True)
    customer_email: Mapped[str | None] = mapped_column(String(200), index=True, nullable=True)
    customer_cpf: Mapped[str | None] = mapped_column(String(20), index=True, nullable=True)
    discount_amount: Mapped[Decimal] = mapped_column(MONEY_COLUMN, default=Decimal("0.00"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    coupon: Mapped[Coupon] = relationship(back_populates="redemptions")
    order: Mapped[Order] = relationship(back_populates="coupon_redemptions")

    def to_dict(self):
        return {
            "id": self.id,
            "coupon_id": self.coupon_id,
            "order_id": self.order_id,
            "customer_email": self.customer_email,
            "customer_cpf": self.customer_cpf,
            "discount_amount": decimal_to_float(self.discount_amount),
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
