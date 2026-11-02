"""Schede clienti e visite."""

from datetime import date, datetime, timedelta
from typing import Annotated, NamedTuple

from email_validator import EmailNotValidError, validate_email
from fastapi import APIRouter, Form, HTTPException, Request
from fastapi.responses import RedirectResponse, Response
from pydantic import BaseModel
from sqlalchemy import case, func, or_, select
from sqlalchemy.orm import Session

from app.dates import parse_day, parse_start
from app.deps import CurrentUser, DbSession
from app.insights import customer_loyalty, loyalty_score
from app.models import Appointment, Customer, Quote, User, Visit
from app.models import Request as PipelineRequest
from app.money import parse_euro
from app.phone import normalize_phone
from app.templating import templates

router = APIRouter(prefix="/clienti")

MAX_NOTES_LENGTH = 5000


class CustomerForm(BaseModel):
    first_name: str = ""
    last_name: str = ""
    phone: str = ""
    email: str = ""
    birth_date: str = ""
    notes: str = ""


def clean_customer_form(form: CustomerForm) -> tuple[dict, dict]:
    """Controlla il form. Restituisce (valori puliti, errori per campo)."""
    values = {
        "first_name": form.first_name.strip(),
        "last_name": form.last_name.strip(),
        "phone": form.phone.strip(),
        "email": form.email.strip() or None,
        "birth_date": None,
        "notes": form.notes.strip() or None,
    }
    errors = {}
    # maxlength nel form non basta: chiunque può mandare la richiesta a mano,
    # e su PostgreSQL un testo troppo lungo fa fallire il salvataggio
    for field, label in (("first_name", "il nome"), ("last_name", "il cognome")):
        if not values[field]:
            errors[field] = f"Manca {label}."
        elif len(values[field]) > 100:
            errors[field] = "Massimo 100 caratteri."
    if values["notes"] and len(values["notes"]) > MAX_NOTES_LENGTH:
        errors["notes"] = f"Massimo {MAX_NOTES_LENGTH} caratteri."
    try:
        values["phone"] = normalize_phone(values["phone"])
    except ValueError:
        errors["phone"] = "Numero non valido. Esempio: 333 123 4567"
    if values["email"]:
        try:
            values["email"] = validate_email(
                values["email"], check_deliverability=False
            ).normalized
        except EmailNotValidError:
            errors["email"] = "Email non valida."
    if form.birth_date.strip():
        try:
            values["birth_date"] = parse_day(form.birth_date)
        except ValueError:
            errors["birth_date"] = "Data non valida."
        else:
            if values["birth_date"] > date.today():
                errors["birth_date"] = "La data di nascita è nel futuro."
    return values, errors


def get_customer(db: Session, user: User, customer_id: int) -> Customer:
    """Il cliente, solo se appartiene all'attività dell'utente. Altrimenti 404."""
    customer = db.scalar(
        select(Customer).where(
            Customer.id == customer_id, Customer.business_id == user.business_id
        )
    )
    if customer is None:
        raise HTTPException(status_code=404, detail="Cliente non trovato")
    return customer


def is_htmx(request: Request) -> bool:
    # Col tasto "indietro" htmx ricarica la pagina intera mandando anche questo header
    return (
        request.headers.get("HX-Request") == "true"
        and request.headers.get("HX-History-Restore-Request") != "true"
    )


class CustomerRow(NamedTuple):
    customer: Customer
    last_visit: date | None
    score: int


SORT_OPTIONS = ("nome", "ultima", "fedelta")


def find_customers(db: Session, business_id: int, q: str, sort: str) -> list[CustomerRow]:
    since = date.today() - timedelta(days=365)
    last_year = Visit.visited_on >= since
    query = (
        select(
            Customer,
            func.max(Visit.visited_on),
            func.count(case((last_year, Visit.id))),
            func.coalesce(func.sum(case((last_year, Visit.amount_cents), else_=0)), 0),
        )
        .outerjoin(Customer.visits)
        .where(Customer.business_id == business_id)
        .group_by(Customer.id)
    )
    # Ogni parola cercata deve comparire nel nome, nel cognome o nel telefono.
    # Limitate: ogni parola aggiunge una condizione alla query.
    for word in q[:100].split()[:5]:
        pattern = f"%{word}%"
        query = query.where(
            or_(
                Customer.first_name.ilike(pattern),
                Customer.last_name.ilike(pattern),
                Customer.phone.like(pattern),
            )
        )
    rows = [
        CustomerRow(customer, last_visit, loyalty_score(visits, cents))
        for customer, last_visit, visits, cents in db.execute(query)
    ]
    # I clienti di una piccola attività sono poche centinaia: ordinare qui è più
    # semplice che rifare il punteggio in SQL
    rows.sort(key=lambda row: (row.customer.last_name.lower(), row.customer.first_name.lower()))
    if sort == "ultima":
        rows.sort(key=lambda row: row.last_visit or date.min, reverse=True)
    elif sort == "fedelta":
        rows.sort(key=lambda row: row.score, reverse=True)
    return rows


@router.get("")
def customer_list(
    request: Request, db: DbSession, user: CurrentUser, q: str = "", ordina: str = "nome"
):
    sort = ordina if ordina in SORT_OPTIONS else "nome"
    rows = find_customers(db, user.business_id, q, sort)
    partial = is_htmx(request)
    context = {"user": user, "rows": rows, "q": q, "sort": sort, "partial": partial}
    template = "customers/_table.html" if partial else "customers/list.html"
    response = templates.TemplateResponse(request, template, context)
    # Stesso indirizzo, risposta diversa con o senza htmx: il browser non deve confonderle
    response.headers["Vary"] = "HX-Request"
    return response


@router.get("/nuovo")
def new_customer_page(request: Request, user: CurrentUser):
    context = {"user": user, "form": CustomerForm(), "errors": {}}
    return templates.TemplateResponse(request, "customers/form.html", context)


@router.post("/nuovo")
def create_customer(
    request: Request,
    db: DbSession,
    user: CurrentUser,
    form: Annotated[CustomerForm, Form()],
):
    values, errors = clean_customer_form(form)
    if errors:
        context = {"user": user, "form": form, "errors": errors}
        return templates.TemplateResponse(
            request, "customers/form.html", context, status_code=400
        )
    customer = Customer(business_id=user.business_id, **values)
    db.add(customer)
    db.commit()
    return RedirectResponse(f"/clienti/{customer.id}", status_code=303)


@router.get("/{customer_id}")
def customer_detail(request: Request, db: DbSession, user: CurrentUser, customer_id: int):
    customer = get_customer(db, user, customer_id)
    today = date.today()
    context = {
        "user": user,
        "customer": customer,
        "today": today,
        "score": customer_loyalty(customer, today),
        "now": datetime.now(),
    }
    return templates.TemplateResponse(request, "customers/detail.html", context)


@router.get("/{customer_id}/note")
def notes_view(request: Request, db: DbSession, user: CurrentUser, customer_id: int):
    customer = get_customer(db, user, customer_id)
    return templates.TemplateResponse(request, "customers/_notes.html", {"customer": customer})


@router.get("/{customer_id}/note/modifica")
def notes_edit(request: Request, db: DbSession, user: CurrentUser, customer_id: int):
    customer = get_customer(db, user, customer_id)
    context = {"customer": customer, "editing": True}
    return templates.TemplateResponse(request, "customers/_notes.html", context)


@router.post("/{customer_id}/note")
def notes_save(
    request: Request,
    db: DbSession,
    user: CurrentUser,
    customer_id: int,
    notes: Annotated[str, Form()] = "",
):
    customer = get_customer(db, user, customer_id)
    if len(notes.strip()) > MAX_NOTES_LENGTH:
        context = {
            "customer": customer,
            "editing": True,
            "error": f"Massimo {MAX_NOTES_LENGTH} caratteri.",
        }
        return templates.TemplateResponse(request, "customers/_notes.html", context)
    customer.notes = notes.strip() or None
    db.commit()
    return templates.TemplateResponse(request, "customers/_notes.html", {"customer": customer})


@router.get("/{customer_id}/modifica")
def edit_customer_page(
    request: Request, db: DbSession, user: CurrentUser, customer_id: int
):
    customer = get_customer(db, user, customer_id)
    form = CustomerForm(
        first_name=customer.first_name,
        last_name=customer.last_name,
        phone=customer.phone,
        email=customer.email or "",
        birth_date=customer.birth_date.isoformat() if customer.birth_date else "",
        notes=customer.notes or "",
    )
    context = {"user": user, "form": form, "errors": {}, "customer": customer}
    return templates.TemplateResponse(request, "customers/form.html", context)


@router.post("/{customer_id}/modifica")
def update_customer(
    request: Request,
    db: DbSession,
    user: CurrentUser,
    customer_id: int,
    form: Annotated[CustomerForm, Form()],
):
    customer = get_customer(db, user, customer_id)
    values, errors = clean_customer_form(form)
    if errors:
        context = {"user": user, "form": form, "errors": errors, "customer": customer}
        return templates.TemplateResponse(
            request, "customers/form.html", context, status_code=400
        )
    for field, value in values.items():
        setattr(customer, field, value)
    db.commit()
    return RedirectResponse(f"/clienti/{customer.id}", status_code=303)


@router.post("/{customer_id}/elimina")
def delete_customer(request: Request, db: DbSession, user: CurrentUser, customer_id: int):
    customer = get_customer(db, user, customer_id)
    # Richieste e preventivi restano: perdono il collegamento ma tengono il nome
    for item in db.scalars(select(PipelineRequest).where(PipelineRequest.customer_id == customer.id)):
        item.contact_name = customer.full_name
        item.customer_id = None
    for quote in db.scalars(select(Quote).where(Quote.customer_id == customer.id)):
        quote.customer_id = None
    db.delete(customer)
    db.commit()
    if is_htmx(request):
        return Response(headers={"HX-Redirect": "/clienti"})
    return RedirectResponse("/clienti", status_code=303)


def visits_section(request: Request, customer: Customer, error: str | None = None):
    """Il pezzo di pagina con le visite: htmx lo sostituisce senza ricaricare tutto."""
    today = date.today()
    context = {
        "customer": customer,
        "today": today,
        "score": customer_loyalty(customer, today),
        "visit_error": error,
    }
    return templates.TemplateResponse(request, "customers/_visits.html", context)


@router.get("/{customer_id}/visite")
def visits_view(request: Request, db: DbSession, user: CurrentUser, customer_id: int):
    return visits_section(request, get_customer(db, user, customer_id))


@router.post("/{customer_id}/visite")
def add_visit(
    request: Request,
    db: DbSession,
    user: CurrentUser,
    customer_id: int,
    visited_on: Annotated[str, Form()] = "",
    amount: Annotated[str, Form()] = "",
    note: Annotated[str, Form()] = "",
):
    customer = get_customer(db, user, customer_id)
    try:
        day = parse_day(visited_on)
    except ValueError:
        return visits_section(request, customer, "Data non valida.")
    if day > date.today():
        return visits_section(request, customer, "La data è nel futuro.")
    try:
        cents = parse_euro(amount)
    except ValueError:
        return visits_section(request, customer, "Importo non valido. Esempio: 25,50")

    customer.visits.append(
        Visit(visited_on=day, amount_cents=cents, note=note.strip()[:255] or None)
    )
    db.commit()
    # Ricarica le visite per averle nell'ordine giusto (dalla più recente)
    db.refresh(customer)
    return visits_section(request, customer)


@router.post("/{customer_id}/visite/{visit_id}/elimina")
def delete_visit(
    request: Request, db: DbSession, user: CurrentUser, customer_id: int, visit_id: int
):
    customer = get_customer(db, user, customer_id)
    visit = next((v for v in customer.visits if v.id == visit_id), None)
    if visit is None:
        raise HTTPException(status_code=404, detail="Visita non trovata")
    customer.visits.remove(visit)
    db.commit()
    return visits_section(request, customer)


def appointments_section(request: Request, customer: Customer, error: str | None = None):
    context = {"customer": customer, "now": datetime.now(), "appointment_error": error}
    return templates.TemplateResponse(request, "customers/_appointments.html", context)


@router.post("/{customer_id}/appuntamenti")
def add_appointment(
    request: Request,
    db: DbSession,
    user: CurrentUser,
    customer_id: int,
    day: Annotated[str, Form()] = "",
    hour: Annotated[str, Form()] = "",
    service: Annotated[str, Form()] = "",
):
    customer = get_customer(db, user, customer_id)
    try:
        starts_at = parse_start(day, hour)
    except ValueError:
        return appointments_section(request, customer, "Scegli giorno e ora.")
    customer.appointments.append(
        Appointment(starts_at=starts_at, service=service.strip()[:100] or None)
    )
    db.commit()
    db.refresh(customer)
    return appointments_section(request, customer)
