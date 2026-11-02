"""Un'attività (salone, palestra, negozio...) con i suoi utenti e clienti."""

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base

if TYPE_CHECKING:  # solo per i type hint, evita import circolari
    from app.models.customer import Customer
    from app.models.movement import Movement
    from app.models.product import Product
    from app.models.quote import Quote
    from app.models.request import Request
    from app.models.user import User


class Business(Base):
    __tablename__ = "businesses"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100))
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())

    # Cancellando l'attività se ne va tutto quello che le appartiene.
    # Preventivi e richieste prima dei clienti, perché possono puntare a loro.
    quotes: Mapped[list["Quote"]] = relationship(cascade="all, delete-orphan")
    requests: Mapped[list["Request"]] = relationship(cascade="all, delete-orphan")
    movements: Mapped[list["Movement"]] = relationship(cascade="all, delete-orphan")
    products: Mapped[list["Product"]] = relationship(cascade="all, delete-orphan")
    users: Mapped[list["User"]] = relationship(
        back_populates="business", cascade="all, delete-orphan"
    )
    customers: Mapped[list["Customer"]] = relationship(
        back_populates="business", cascade="all, delete-orphan"
    )
