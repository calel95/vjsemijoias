from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base, utc_now


class Payment(Base):
    __tablename__ = "payments"

    id: Mapped[int] = mapped_column(primary_key=True)
    order_id: Mapped[str] = mapped_column(ForeignKey("orders.id"), unique=True)
    provider: Mapped[str] = mapped_column(String(30), default="infinitepay")
    provider_order_id: Mapped[str | None] = mapped_column(
        String(100), unique=True, nullable=True
    )
    provider_payment_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    checkout_token: Mapped[str] = mapped_column(String(100), unique=True)
    checkout_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    method: Mapped[str] = mapped_column(String(30))
    status: Mapped[str] = mapped_column(String(50), default="pending")
    status_detail: Mapped[str | None] = mapped_column(String(100), nullable=True)
    pix_qr_code: Mapped[str | None] = mapped_column(Text, nullable=True)
    pix_qr_code_base64: Mapped[str | None] = mapped_column(Text, nullable=True)
    pix_ticket_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, onupdate=utc_now
    )
    order: Mapped[Order] = relationship(back_populates="payment")

    def to_dict(self, include_pix=True):
        data = {
            "order_id": self.order_id,
            "provider": self.provider,
            "provider_order_id": self.provider_order_id,
            "provider_payment_id": self.provider_payment_id,
            "method": self.method,
            "status": self.status,
            "status_detail": self.status_detail,
            "checkout_token": self.checkout_token,
            "checkout_url": self.checkout_url,
        }
        if include_pix and self.method == "pix":
            data.update(
                {
                    "pix_qr_code": self.pix_qr_code,
                    "pix_qr_code_base64": self.pix_qr_code_base64,
                    "pix_ticket_url": self.pix_ticket_url,
                }
            )
        return data
