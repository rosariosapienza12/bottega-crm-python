"""Agenda settimanale degli appuntamenti."""

from datetime import date, datetime, timedelta
from typing import Annotated

from fastapi import APIRouter, Form, HTTPException, Request
from fastapi.responses import Response
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.dates import parse_day, parse_start
from app.deps import CurrentUser, DbSession
from app.models import Appointment, Customer, User, Visit
from app.money import parse_euro
from app.templating import templates

router = APIRouter()

DAY_NAMES = ["Lunedì", "Martedì", "Mercoledì", "Giovedì", "Venerdì", "Sabato", "Domenica"]


def monday_of(day: date) -> date:
    return day - timedelta(days=day.weekday())


def appointments_between(db: Session, business_id: int, start: datetime, end: datetime):
    return db.scalars(
        select(Appointment)
        .join(Appointment.customer)
        .where(
            Customer.business_id == business_id,
            Appointment.starts_at >= start,
            Appointment.starts_at < end,
        )
        .order_by(Appointment.starts_at)
    ).all()


def render_agenda(
    request: Request,
    db: Session,
    user: User,
    monday: date,
    error: str | None = None,
    status_code: int = 200,
):
    start = datetime.combine(monday, datetime.min.time())
    appointments = appointments_between(db, user.business_id, start, start + timedelta(days=7))
    days = []
    for offset in range(7):
        day = monday + timedelta(days=offset)
        items = [a for a in appointments if a.starts_at.date() == day]
        days.append({"date": day, "name": DAY_NAMES[offset], "appointments": items})
    customers = db.scalars(
        select(Customer)
        .where(Customer.business_id == user.business_id)
        .order_by(Customer.last_name, Customer.first_name)
    ).all()
    context = {
        "user": user,
        "monday": monday,
        "sunday": monday + timedelta(days=6),
        "previous": monday - timedelta(days=7),
        "next": monday + timedelta(days=7),
        "this_monday": monday_of(date.today()),
        "days": days,
        "customers": customers,
        "now": datetime.now(),
        "today": date.today(),
        "error": error,
    }
    return templates.TemplateResponse(request, "agenda.html", context, status_code=status_code)


@router.get("/agenda")
def agenda(request: Request, db: DbSession, user: CurrentUser, settimana: str = ""):
    try:
        monday = monday_of(parse_day(settimana))
    except ValueError:
        monday = monday_of(date.today())
    return render_agenda(request, db, user, monday)


@router.post("/agenda")
def add_appointment_from_agenda(
    request: Request,
    db: DbSession,
    user: CurrentUser,
    customer_id: Annotated[int, Form()],
    day: Annotated[str, Form()] = "",
    hour: Annotated[str, Form()] = "",
    service: Annotated[str, Form()] = "",
):
    customer = db.scalar(
        select(Customer).where(
            Customer.id == customer_id, Customer.business_id == user.business_id
        )
    )
    if customer is None:
        raise HTTPException(status_code=404, detail="Cliente non trovato")
    try:
        starts_at = parse_start(day, hour)
    except ValueError:
        return render_agenda(
            request, db, user, monday_of(date.today()), "Scegli giorno e ora.", 422
        )
    db.add(Appointment(customer=customer, starts_at=starts_at, service=service.strip()[:100] or None))
    db.commit()
    # Mostra la settimana in cui è finito il nuovo appuntamento
    return render_agenda(request, db, user, monday_of(starts_at.date()))


def get_appointment(db: Session, user: User, appointment_id: int) -> Appointment:
    appointment = db.scalar(
        select(Appointment)
        .join(Appointment.customer)
        .where(Appointment.id == appointment_id, Customer.business_id == user.business_id)
    )
    if appointment is None:
        raise HTTPException(status_code=404, detail="Appuntamento non trovato")
    return appointment


@router.post("/appuntamenti/{appointment_id}/fatto")
def appointment_done(
    db: DbSession,
    user: CurrentUser,
    appointment_id: int,
    amount: Annotated[str, Form()] = "",
):
    """L'appuntamento c'è stato: diventa una visita con l'incasso."""
    appointment = get_appointment(db, user, appointment_id)
    if appointment.starts_at > datetime.now():
        raise HTTPException(status_code=400, detail="Appuntamento non ancora iniziato")
    try:
        cents = parse_euro(amount)
    except ValueError:
        # Il campo ha già un "pattern" che lo blocca nel browser: qui arriva solo
        # chi aggira il form. Con un 400 htmx non tocca la riga (vedi base.html)
        return Response("Importo non valido", status_code=400)
    db.add(
        Visit(
            customer_id=appointment.customer_id,
            visited_on=appointment.starts_at.date(),
            amount_cents=cents,
            note=appointment.service,
        )
    )
    db.delete(appointment)
    db.commit()
    # Risposta vuota: htmx toglie la riga. L'evento fa aggiornare le visite nella scheda.
    return Response(headers={"HX-Trigger": "visitsChanged"})


@router.post("/appuntamenti/{appointment_id}/annulla")
def appointment_cancel(db: DbSession, user: CurrentUser, appointment_id: int):
    db.delete(get_appointment(db, user, appointment_id))
    db.commit()
    return Response()
