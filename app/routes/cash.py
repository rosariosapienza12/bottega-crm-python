"""Cassa: entrate e uscite del mese, con le visite già conteggiate."""

from datetime import date
from typing import Annotated

from fastapi import APIRouter, Form, HTTPException, Request
from fastapi.responses import Response
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.cash import add_months, expenses_by_category, last_months, month_cash, month_start
from app.dates import parse_day
from app.deps import CurrentUser, DbSession
from app.models import Customer, Movement, User, Visit
from app.models.movement import EXPENSE_CATEGORIES, INCOME_CATEGORIES
from app.money import parse_euro
from app.templating import templates

router = APIRouter(prefix="/cassa")


def parse_month(raw: str, today: date) -> date:
    """ "2026-11" -> 1 novembre 2026. Se non è un mese sensato, il mese in corso."""
    try:
        return month_start(parse_day(f"{raw}-01"))
    except ValueError:
        return month_start(today)


def month_entries(db: Session, business_id: int, start: date) -> list[dict]:
    """Visite e movimenti del mese in un'unica lista, dal più recente."""
    end = add_months(start, 1)
    visits = db.execute(
        select(Visit, Customer)
        .join(Visit.customer)
        .where(
            Customer.business_id == business_id,
            Visit.visited_on >= start,
            Visit.visited_on < end,
            Visit.amount_cents > 0,
        )
    ).all()
    movements = db.scalars(
        select(Movement).where(
            Movement.business_id == business_id,
            Movement.occurred_on >= start,
            Movement.occurred_on < end,
        )
    ).all()
    entries = [
        {
            "day": visit.visited_on,
            "kind": "entrata",
            "cents": visit.amount_cents,
            "what": visit.note or "Visita",
            "who": customer,
            "movement": None,
        }
        for visit, customer in visits
    ] + [
        {
            "day": m.occurred_on,
            "kind": m.kind,
            "cents": m.amount_cents,
            "what": m.category + (f": {m.note}" if m.note else ""),
            "who": None,
            "movement": m,
        }
        for m in movements
    ]
    return sorted(entries, key=lambda e: e["day"], reverse=True)


def render_cash(request: Request, db: Session, user: User, start: date, error=None):
    today = date.today()
    context = {
        "user": user,
        "start": start,
        "previous": add_months(start, -1),
        "next": add_months(start, 1),
        "is_current": start == month_start(today),
        "today": today,
        "summary": month_cash(db, user.business_id, start),
        "months": last_months(db, user.business_id, today),
        "categories": expenses_by_category(db, user.business_id, start),
        "entries": month_entries(db, user.business_id, start),
        "expense_categories": EXPENSE_CATEGORIES,
        "income_categories": INCOME_CATEGORIES,
        "error": error,
    }
    # 422 e non 400: htmx è configurato (base.html) per mostrare i 422,
    # cioè gli errori nei dati del form, e ignorare gli altri errori
    return templates.TemplateResponse(
        request, "cash.html", context, status_code=422 if error else 200
    )


@router.get("")
def cash_page(request: Request, db: DbSession, user: CurrentUser, mese: str = ""):
    return render_cash(request, db, user, parse_month(mese, date.today()))


@router.post("")
def add_movement(
    request: Request,
    db: DbSession,
    user: CurrentUser,
    kind: Annotated[str, Form()] = "uscita",
    occurred_on: Annotated[str, Form()] = "",
    amount: Annotated[str, Form()] = "",
    category: Annotated[str, Form()] = "",
    note: Annotated[str, Form()] = "",
):
    today = date.today()
    try:
        day = parse_day(occurred_on)
    except ValueError:
        return render_cash(request, db, user, month_start(today), "Data non valida.")
    categories = {"uscita": EXPENSE_CATEGORIES, "entrata": INCOME_CATEGORIES}
    if category not in categories.get(kind, []):
        return render_cash(request, db, user, month_start(day), "Scegli tipo e categoria.")
    try:
        cents = parse_euro(amount)
    except ValueError:
        cents = 0
    if cents <= 0:
        return render_cash(request, db, user, month_start(day), "Importo non valido. Esempio: 45,90")
    db.add(
        Movement(
            business_id=user.business_id,
            kind=kind,
            occurred_on=day,
            amount_cents=cents,
            category=category,
            note=note.strip()[:200] or None,
        )
    )
    db.commit()
    return render_cash(request, db, user, month_start(day))


@router.post("/{movement_id}/elimina")
def delete_movement(db: DbSession, user: CurrentUser, movement_id: int):
    movement = db.scalar(
        select(Movement).where(
            Movement.id == movement_id, Movement.business_id == user.business_id
        )
    )
    if movement is None:
        raise HTTPException(status_code=404, detail="Movimento non trovato")
    db.delete(movement)
    db.commit()
    return Response()
