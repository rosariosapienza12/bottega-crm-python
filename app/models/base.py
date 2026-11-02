"""Classe base dei modelli, tenuta separata dalla connessione al database."""

from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    pass
