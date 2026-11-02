"""Un'attività (salone, palestra, negozio...) con i suoi utenti e clienti."""

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base

if TYPE_CHECKING:  # solo per i type hint, evita import circolari
    from app.models.customer import Customer
    from app.models.user import User


class Business(Base):
    __tablename__ = "businesses"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100))
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())

    # Cancellando l'attività si cancellano anche i suoi utenti e clienti
    users: Mapped[list["User"]] = relationship(
        back_populates="business", cascade="all, delete-orphan"
    )
    customers: Mapped[list["Customer"]] = relationship(
        back_populates="business", cascade="all, delete-orphan"
    )
