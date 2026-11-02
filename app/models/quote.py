"""Preventivi: righe con prezzo e costo, sconto e IVA."""

from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, Numeric, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base
from app.quotes import line_total_cents

if TYPE_CHECKING:
    from app.models.customer import Customer
    from app.models.request import Request


class Quote(Base):
    __tablename__ = "quotes"

    id: Mapped[int] = mapped_column(primary_key=True)
    business_id: Mapped[int] = mapped_column(ForeignKey("businesses.id"), index=True)
    # SET NULL: se il cliente o la richiesta spariscono, il preventivo resta
    customer_id: Mapped[int | None] = mapped_column(
        ForeignKey("customers.id", ondelete="SET NULL"), index=True
    )
    request_id: Mapped[int | None] = mapped_column(
        ForeignKey("requests.id", ondelete="SET NULL"), index=True
    )
    title: Mapped[str] = mapped_column(String(150))
    discount_percent: Mapped[int] = mapped_column(default=0)
    vat_percent: Mapped[int] = mapped_column(default=22)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())

    customer: Mapped["Customer | None"] = relationship()
    request: Mapped["Request | None"] = relationship(back_populates="quotes")
    lines: Mapped[list["QuoteLine"]] = relationship(
        back_populates="quote", cascade="all, delete-orphan", order_by="QuoteLine.id"
    )


class QuoteLine(Base):
    __tablename__ = "quote_lines"

    id: Mapped[int] = mapped_column(primary_key=True)
    quote_id: Mapped[int] = mapped_column(ForeignKey("quotes.id"), index=True)
    description: Mapped[str] = mapped_column(String(200))
    # Decimale: si possono preventivare anche 1,5 ore
    quantity: Mapped[Decimal] = mapped_column(Numeric(10, 2), default=Decimal(1))
    unit_price_cents: Mapped[int] = mapped_column(default=0)
    # Quanto costa a noi: serve solo per calcolare il margine, non va al cliente
    unit_cost_cents: Mapped[int] = mapped_column(default=0)

    quote: Mapped["Quote"] = relationship(back_populates="lines")

    @property
    def total_cents(self) -> int:
        # Stessa funzione usata per il subtotale: le righe tornano sempre col totale
        return line_total_cents(self.quantity, self.unit_price_cents)
