"""Modello User: una persona che può fare login."""

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

if TYPE_CHECKING:
    from app.models.business import Business


class User(Base):
    """Un utente appartiene a un'attività e vede solo i clienti di quella."""

    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    # Chiave esterna: deve corrispondere a un id esistente in "businesses"
    business_id: Mapped[int] = mapped_column(ForeignKey("businesses.id"), index=True)
    # unique: due utenti non possono avere la stessa email
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    # Mai la password in chiaro: solo il suo hash (Argon2)
    password_hash: Mapped[str] = mapped_column(String(255))
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())

    business: Mapped["Business"] = relationship(back_populates="users")
