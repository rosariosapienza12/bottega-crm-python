"""Tutti i modelli del progetto, importati in un unico punto.

Alembic e SQLAlchemy "vedono" un modello solo se il suo file è stato
importato: importandoli qui, basta scrivere `import app.models`.
"""

from app.models.business import Business
from app.models.customer import Customer
from app.models.user import User

__all__ = ["Business", "Customer", "User"]
