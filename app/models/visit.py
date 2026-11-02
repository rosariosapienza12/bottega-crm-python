"""Una visita (o un acquisto) di un cliente."""

from datetime import date
from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base

if TYPE_CHECKING:
    from app.models.customer import Customer


class Visit(Base):
    __tablename__ = "visits"

    id: Mapped[int] = mapped_column(primary_key=True)
    customer_id: Mapped[int] = mapped_column(ForeignKey("customers.id"), index=True)
    visited_on: Mapped[date]
    # In centesimi: con i float 0.10 + 0.20 non fa 0.30
    amount_cents: Mapped[int] = mapped_column(default=0)
    note: Mapped[str | None] = mapped_column(String(255))

    customer: Mapped["Customer"] = relationship(back_populates="visits")
