"""Un appuntamento in agenda."""

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base

if TYPE_CHECKING:
    from app.models.customer import Customer


class Appointment(Base):
    __tablename__ = "appointments"

    id: Mapped[int] = mapped_column(primary_key=True)
    customer_id: Mapped[int] = mapped_column(ForeignKey("customers.id"), index=True)
    # Ora locale dell'attività, senza fuso: un appuntamento alle 15 resta alle 15
    starts_at: Mapped[datetime] = mapped_column(index=True)
    service: Mapped[str | None] = mapped_column(String(100))

    customer: Mapped["Customer"] = relationship(back_populates="appointments")
