"""Un cliente di un'attività."""

from datetime import date, datetime
from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base

if TYPE_CHECKING:
    from app.models.appointment import Appointment
    from app.models.business import Business
    from app.models.visit import Visit


class Customer(Base):
    __tablename__ = "customers"

    id: Mapped[int] = mapped_column(primary_key=True)
    # Quasi ogni query filtra per attività
    business_id: Mapped[int] = mapped_column(ForeignKey("businesses.id"), index=True)

    first_name: Mapped[str] = mapped_column(String(100))
    last_name: Mapped[str] = mapped_column(String(100))
    # Formato internazionale (+39...), è quello che vuole wa.me
    phone: Mapped[str] = mapped_column(String(20))
    # Non unica: capita che madre e figlia usino la stessa email
    email: Mapped[str | None] = mapped_column(String(255))
    birth_date: Mapped[date | None]
    notes: Mapped[str | None] = mapped_column(Text)

    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        server_default=func.now(), onupdate=func.now()
    )

    business: Mapped["Business"] = relationship(back_populates="customers")
    # Dalla più recente
    visits: Mapped[list["Visit"]] = relationship(
        back_populates="customer",
        cascade="all, delete-orphan",
        order_by="(desc(Visit.visited_on), desc(Visit.id))",
    )
    appointments: Mapped[list["Appointment"]] = relationship(
        back_populates="customer",
        cascade="all, delete-orphan",
        order_by="Appointment.starts_at",
    )

    @property
    def full_name(self) -> str:
        return f"{self.first_name} {self.last_name}"
