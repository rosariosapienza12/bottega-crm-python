"""Importare questo pacchetto registra tutti i modelli (serve ad Alembic)."""

from app.models.base import Base
from app.models.business import Business
from app.models.customer import Customer
from app.models.user import User

__all__ = ["Base", "Business", "Customer", "User"]
