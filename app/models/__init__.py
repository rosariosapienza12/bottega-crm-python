"""Importare questo pacchetto registra tutti i modelli (serve ad Alembic)."""

from app.models.appointment import Appointment
from app.models.base import Base
from app.models.business import Business
from app.models.customer import Customer
from app.models.user import User
from app.models.visit import Visit

__all__ = ["Appointment", "Base", "Business", "Customer", "User", "Visit"]
