"""Chi può fare login. Appartiene a una sola attività."""

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base

if TYPE_CHECKING:
    from app.models.business import Business


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    business_id: Mapped[int] = mapped_column(ForeignKey("businesses.id"), index=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    # Hash Argon2, la password in chiaro non si salva mai
    password_hash: Mapped[str] = mapped_column(String(255))
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())

    business: Mapped["Business"] = relationship(back_populates="users")
