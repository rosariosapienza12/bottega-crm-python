"""Modello Business: un'attività (salone, palestra, negozio...)."""

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

# Questi import servono solo all'editor per i suggerimenti sui tipi:
# a runtime non vengono eseguiti, così evitiamo import circolari.
if TYPE_CHECKING:
    from app.models.customer import Customer
    from app.models.user import User


class Business(Base):
    """Un'attività: ha i suoi utenti (chi fa login) e i suoi clienti."""

    __tablename__ = "businesses"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100))
    # La data la mette il database al momento dell'inserimento
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())

    # Relazioni: business.users e business.customers danno le liste collegate
    users: Mapped[list["User"]] = relationship(back_populates="business")
    customers: Mapped[list["Customer"]] = relationship(back_populates="business")
