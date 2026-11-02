"""Dipendenze FastAPI condivise: sessione del database e utente loggato."""

from typing import Annotated

from fastapi import Depends, Request
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import User


class LoginRequired(Exception):
    """Pagina riservata aperta senza login: main.py la trasforma in un redirect."""


def current_user(request: Request, db: Annotated[Session, Depends(get_db)]) -> User:
    user_id = request.session.get("user_id")
    user = db.get(User, user_id) if user_id is not None else None
    if user is None:
        raise LoginRequired()
    return user


DbSession = Annotated[Session, Depends(get_db)]
CurrentUser = Annotated[User, Depends(current_user)]
