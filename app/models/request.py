"""Una richiesta nella pipeline: dal primo contatto alla conferma (o no)."""

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base

if TYPE_CHECKING:
    from app.models.customer import Customer
    from app.models.quote import Quote

# (chiave salvata nel database, nome della colonna nella pipeline)
STAGES = [
    ("nuova", "Nuove"),
    ("contattata", "Contattate"),
    ("preventivo", "Preventivo inviato"),
    ("confermata", "Confermate"),
    ("persa", "Perse"),
]
STAGE_KEYS = [key for key, _ in STAGES]


class Request(Base):
    __tablename__ = "requests"

    id: Mapped[int] = mapped_column(primary_key=True)
    business_id: Mapped[int] = mapped_column(ForeignKey("businesses.id"), index=True)
    # Può arrivare da qualcuno che non è ancora cliente: allora basta il nome
    customer_id: Mapped[int | None] = mapped_column(
        ForeignKey("customers.id", ondelete="SET NULL"), index=True
    )
    contact_name: Mapped[str | None] = mapped_column(String(100))
    title: Mapped[str] = mapped_column(String(150))
    value_cents: Mapped[int] = mapped_column(default=0)
    stage: Mapped[str] = mapped_column(String(20), default="nuova")
    # Ordine dentro la colonna, cambia col trascinamento
    position: Mapped[int] = mapped_column(default=0)
    notes: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())

    customer: Mapped["Customer | None"] = relationship()
    quotes: Mapped[list["Quote"]] = relationship(back_populates="request")

    @property
    def who(self) -> str:
        return self.customer.full_name if self.customer else (self.contact_name or "")
