"""Movimenti di cassa scritti a mano: spese e incassi che non sono visite."""

from datetime import date

from sqlalchemy import ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base

EXPENSE_CATEGORIES = ["Prodotti", "Affitto", "Bollette", "Stipendi", "Attrezzatura", "Altro"]
INCOME_CATEGORIES = ["Vendita prodotti", "Buono regalo", "Altro"]


class Movement(Base):
    __tablename__ = "movements"

    id: Mapped[int] = mapped_column(primary_key=True)
    business_id: Mapped[int] = mapped_column(ForeignKey("businesses.id"), index=True)
    # "entrata" o "uscita"; l'importo è sempre positivo
    kind: Mapped[str] = mapped_column(String(10))
    occurred_on: Mapped[date] = mapped_column(index=True)
    amount_cents: Mapped[int]
    category: Mapped[str] = mapped_column(String(50))
    note: Mapped[str | None] = mapped_column(String(200))
