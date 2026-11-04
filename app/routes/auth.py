"""Registrazione, login e logout."""

from typing import Annotated

from email_validator import EmailNotValidError, validate_email
from fastapi import APIRouter, Form, HTTPException, Request
from fastapi.responses import RedirectResponse
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.config import settings
from app.deps import DbSession
from app.models import Business, User
from app.ratelimit import ip_limiter, login_limiter, signup_limiter
from app.security import hash_password, verify_password
from app.templating import templates

router = APIRouter()

# L'account creato da scripts/crea_demo.py
DEMO_EMAIL = "demo@bottega.test"

MIN_PASSWORD_LENGTH = 8
# Un limite in alto serve solo a non far calcolare l'hash di testi enormi
MAX_PASSWORD_LENGTH = 200

# Hash di una password a caso: se l'email non esiste verifichiamo comunque
# qualcosa, così la risposta ci mette lo stesso tempo e non rivela chi è iscritto
_DUMMY_HASH = hash_password("password-che-non-esiste")


def start_session(request: Request, user: User) -> RedirectResponse:
    # clear() prima di salvare l'id: un vecchio cookie non deve sopravvivere al login
    request.session.clear()
    request.session["user_id"] = user.id
    request.session["version"] = user.session_version
    return RedirectResponse("/panoramica", status_code=303)


def client_ip(request: Request) -> str:
    return request.client.host if request.client else "sconosciuto"


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

    ip_key = f"ip:{client_ip(request)}"
    if signup_limiter.is_blocked(ip_key):
        context = {"error": "Troppe registrazioni da questa rete. Riprova più tardi.", "email": email}
        return templates.TemplateResponse(request, "auth/register.html", context, status_code=429)
    signup_limiter.record(ip_key)

    if not business_name:
        error = "Scrivi il nome della tua attività."
    elif len(business_name) > 100:
        error = "Il nome dell'attività può avere al massimo 100 caratteri."
    else:
        try:
            email = validate_email(email, check_deliverability=False).normalized.lower()
        except EmailNotValidError:
            error = "L'email non sembra giusta."

    if error is None and not MIN_PASSWORD_LENGTH <= len(password) <= MAX_PASSWORD_LENGTH:
        error = f"La password deve avere da {MIN_PASSWORD_LENGTH} a {MAX_PASSWORD_LENGTH} caratteri."
    if error is None and db.scalar(select(User.id).where(User.email == email)):
        error = "Esiste già un account con questa email."

    if error is None:
        user = User(
            email=email,
            password_hash=hash_password(password),
            business=Business(name=business_name),
        )
        db.add(user)
        try:
            db.commit()
        except IntegrityError:
            # Due registrazioni con la stessa email nello stesso istante:
            # il controllo sopra non basta, decide l'indice unique del database
            db.rollback()
            error = "Esiste già un account con questa email."
        else:
            return start_session(request, user)

    context = {"error": error, "business_name": business_name, "email": email}
    return templates.TemplateResponse(request, "auth/register.html", context, status_code=400)


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
    email = email.strip().lower()[:255]
    ip_key = f"ip:{client_ip(request)}"
    pair_key = f"{ip_key}|email:{email}"
    if login_limiter.is_blocked(pair_key) or ip_limiter.is_blocked(ip_key):
        context = {"error": "Troppi tentativi sbagliati. Riprova tra un quarto d'ora.", "email": email}
        return templates.TemplateResponse(request, "auth/login.html", context, status_code=429)

    user = db.scalar(select(User).where(User.email == email))
    password = password[:MAX_PASSWORD_LENGTH]
    if user is None:
        verify_password(password, _DUMMY_HASH)
    if user is None or not verify_password(password, user.password_hash):
        login_limiter.record(pair_key)
        ip_limiter.record(ip_key)
        # Stesso messaggio nei due casi: non diciamo a nessuno se l'email esiste
        context = {"error": "Email o password sbagliate.", "email": email}
        return templates.TemplateResponse(request, "auth/login.html", context, status_code=400)

    login_limiter.reset(pair_key)
    return start_session(request, user)


@router.post("/demo")
def demo_login(request: Request, db: DbSession):
    """Entra nell'attività di prova senza password: esiste solo nella demo online."""
    if not settings.demo_mode:
        raise HTTPException(status_code=404)
    user = db.scalar(select(User).where(User.email == DEMO_EMAIL))
    if user is None:
        return RedirectResponse("/accedi", status_code=303)
    return start_session(request, user)


@router.post("/esci")
def logout(request: Request, db: DbSession):
    user_id = request.session.get("user_id")
    user = db.get(User, user_id) if isinstance(user_id, int) else None
    if user is not None and request.session.get("version") == user.session_version:
        user.session_version += 1
        db.commit()
    request.session.clear()
    return RedirectResponse("/", status_code=303)
