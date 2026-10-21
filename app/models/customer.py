"""Modello Customer: un cliente di un'attività."""

from datetime import date, datetime
from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

if TYPE_CHECKING:
    from app.models.business import Business


class Customer(Base):
    """Un cliente: appartiene a una sola attività e solo lei può vederlo."""

    __tablename__ = "customers"

    id: Mapped[int] = mapped_column(primary_key=True)
    # Indice: quasi ogni ricerca filtra per attività, così è veloce
    business_id: Mapped[int] = mapped_column(ForeignKey("businesses.id"), index=True)

    first_name: Mapped[str] = mapped_column(String(100))
    last_name: Mapped[str] = mapped_column(String(100))
    # Testo e non numero: salviamo il formato internazionale (+393331234567)
    phone: Mapped[str] = mapped_column(String(20))

    # Campi facoltativi: "| None" li rende NULL-abili nel database.
    # L'email non è unique: due clienti (es. madre e figlia) possono condividerla.
    email: Mapped[str | None] = mapped_column(String(255))
    birth_date: Mapped[date | None]
    # Text: nessun limite di lunghezza, adatto alle note libere
    notes: Mapped[str | None] = mapped_column(Text)

    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
    # onupdate: SQLAlchemy aggiorna la data a ogni modifica del cliente
    updated_at: Mapped[datetime] = mapped_column(
        server_default=func.now(), onupdate=func.now()
    )
    business: Mapped["Business"] = relationship(back_populates="customers")
 