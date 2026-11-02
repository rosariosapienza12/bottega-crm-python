"""Importare questo pacchetto registra tutti i modelli (serve ad Alembic)."""

from app.models.appointment import Appointment
from app.models.base import Base
from app.models.business import Business
from app.models.customer import Customer
from app.models.movement import Movement
from app.models.product import Product
from app.models.quote import Quote, QuoteLine
from app.models.request import Request
from app.models.user import User
from app.models.visit import Visit

__all__ = [
    "Appointment",
    "Base",
    "Business",
    "Customer",
    "Movement",
    "Product",
    "Quote",
    "QuoteLine",
    "Request",
    "User",
    "Visit",
]
