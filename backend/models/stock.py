from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base, utc_now


class StockMovement(Base):
    __tablename__ = "stock_movements"

    id: Mapped[int] = mapped_column(primary_key=True)
    produto_id: Mapped[int] = mapped_column(ForeignKey("products.id"), index=True)
    tipo: Mapped[str] = mapped_column(String(20), index=True)
    quantidade: Mapped[int] = mapped_column(Integer)
    saldo_anterior: Mapped[int] = mapped_column(Integer)
    saldo_atual: Mapped[int] = mapped_column(Integer)
    motivo: Mapped[str] = mapped_column(String(200))
    observacoes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_by_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id"), index=True, nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    product: Mapped[Product] = relationship(back_populates="stock_movements")
    created_by: Mapped["User | None"] = relationship("User")

    def to_dict(self):
        delta = self.saldo_atual - self.saldo_anterior
        return {
            "id": self.id,
            "produto_id": self.produto_id,
            "tipo": self.tipo,
            "quantidade": self.quantidade,
            "delta": delta,
            "saldo_anterior": self.saldo_anterior,
            "saldo_atual": self.saldo_atual,
            "motivo": self.motivo,
            "observacoes": self.observacoes,
            "created_by_id": self.created_by_id,
            "created_by": self.created_by.to_dict() if self.created_by else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
