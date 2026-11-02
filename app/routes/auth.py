"""Registrazione, login e logout."""

from typing import Annotated

from email_validator import EmailNotValidError, validate_email
from fastapi import APIRouter, Form, Request
from fastapi.responses import RedirectResponse
from sqlalchemy import select

from app.deps import DbSession
from app.models import Business, User
from app.security import hash_password, verify_password
from app.templating import templates

router = APIRouter()

MIN_PASSWORD_LENGTH = 8


def start_session(request: Request, user: User) -> RedirectResponse:
    # clear() prima di salvare l'id: un vecchio cookie non deve sopravvivere al login
    request.session.clear()
    request.session["user_id"] = user.id
    return RedirectResponse("/panoramica", status_code=303)


@router.get("/registrati")
def register_page(request: Request):
    return templates.TemplateResponse(request, "auth/register.html", {})


@router.post("/registrati")
def register(
    request: Request,
    db: DbSession,
    business_name: Annotated[str, Form()] = "",
    email: Annotated[str, Form()] = "",
    password: Annotated[str, Form()] = "",
):
    business_name = business_name.strip()
    email = email.strip()
    error = None

    if not business_name:
        error = "Scrivi il nome della tua attività."
    elif len(business_name) > 100:
        error = "Il nome dell'attività può avere al massimo 100 caratteri."
    else:
        try:
            email = validate_email(email, check_deliverability=False).normalized.lower()
        except EmailNotValidError:
            error = "L'email non sembra giusta."

    if error is None and len(password) < MIN_PASSWORD_LENGTH:
        error = f"La password deve avere almeno {MIN_PASSWORD_LENGTH} caratteri."
    if error is None and db.scalar(select(User.id).where(User.email == email)):
        error = "Esiste già un account con questa email."

    if error:
        context = {"error": error, "business_name": business_name, "email": email}
        return templates.TemplateResponse(
            request, "auth/register.html", context, status_code=400
        )

    user = User(
        email=email,
        password_hash=hash_password(password),
        business=Business(name=business_name),
    )
    db.add(user)
    db.commit()
    return start_session(request, user)


@router.get("/accedi")
def login_page(request: Request):
    return templates.TemplateResponse(request, "auth/login.html", {})


@router.post("/accedi")
def login(
    request: Request,
    db: DbSession,
    email: Annotated[str, Form()] = "",
    password: Annotated[str, Form()] = "",
):
    email = email.strip().lower()
    user = db.scalar(select(User).where(User.email == email))
    # Stesso messaggio nei due casi: non diciamo a nessuno se l'email esiste
    if user is None or not verify_password(password, user.password_hash):
        context = {"error": "Email o password sbagliate.", "email": email}
        return templates.TemplateResponse(
            request, "auth/login.html", context, status_code=400
        )
    return start_session(request, user)


@router.post("/esci")
def logout(request: Request):
    request.session.clear()
    return RedirectResponse("/", status_code=303)
