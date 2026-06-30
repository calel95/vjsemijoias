from __future__ import annotations

from datetime import date, datetime

from sqlalchemy import Date, DateTime, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base, utc_now


class Customer(Base):
    __tablename__ = "customers"

    id: Mapped[int] = mapped_column(primary_key=True)
    nome: Mapped[str] = mapped_column(String(200), index=True)
    whatsapp: Mapped[str | None] = mapped_column(String(30), nullable=True, index=True)
    email: Mapped[str | None] = mapped_column(String(200), nullable=True, index=True)
    cpf: Mapped[str | None] = mapped_column(String(11), nullable=True, index=True)
    instagram: Mapped[str | None] = mapped_column(String(120), nullable=True, index=True)
    cidade: Mapped[str | None] = mapped_column(String(120), nullable=True, index=True)
    estado: Mapped[str | None] = mapped_column(String(2), nullable=True)
    data_nascimento: Mapped[date | None] = mapped_column(Date, nullable=True)
    observacoes: Mapped[str | None] = mapped_column(Text, nullable=True)
    origem: Mapped[str | None] = mapped_column(String(120), nullable=True, index=True)
    status: Mapped[str] = mapped_column(String(30), default="ativo", index=True)
    created_by_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id"), index=True, nullable=True
    )
    updated_by_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id"), index=True, nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, onupdate=utc_now
    )

    created_by: Mapped["User | None"] = relationship("User", foreign_keys=[created_by_id])
    updated_by: Mapped["User | None"] = relationship("User", foreign_keys=[updated_by_id])
    orders: Mapped[list["VJAdminOrder"]] = relationship(back_populates="customer")

    def to_dict(self):
        return {
            "id": self.id,
            "nome": self.nome,
            "whatsapp": self.whatsapp,
            "email": self.email,
            "cpf": self.cpf,
            "instagram": self.instagram,
            "cidade": self.cidade,
            "estado": self.estado,
            "data_nascimento": self.data_nascimento.isoformat() if self.data_nascimento else None,
            "observacoes": self.observacoes,
            "origem": self.origem,
            "status": self.status,
            "created_by_id": self.created_by_id,
            "updated_by_id": self.updated_by_id,
            "created_by": self.created_by.to_dict() if self.created_by else None,
            "updated_by": self.updated_by.to_dict() if self.updated_by else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }