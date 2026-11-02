"""Preventivatore: righe, sconto, IVA, margine e versione da stampare."""

from typing import Annotated

from fastapi import APIRouter, Form, HTTPException, Request
from fastapi.responses import RedirectResponse, Response
from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload, selectinload

from app.deps import CurrentUser, DbSession
from app.models import Quote, QuoteLine, User
from app.models import Request as PipelineRequest
from app.money import parse_euro
from app.quotes import compute_totals, parse_percent, parse_quantity
from app.routes.pipeline import business_customers, owned_customer_id
from app.templating import templates

router = APIRouter(prefix="/preventivi")

MAX_LINES = 100


def get_quote(db: Session, user: User, quote_id: int) -> Quote:
    quote = db.scalar(
        select(Quote).where(Quote.id == quote_id, Quote.business_id == user.business_id)
    )
    if quote is None:
        raise HTTPException(status_code=404, detail="Preventivo non trovato")
    return quote


def sync_request_value(request_item: PipelineRequest | None) -> None:
    """Una richiesta con preventivi vale quanto il più recente.

    Unica fonte del valore: finché ci sono preventivi, nella richiesta il
    campo valore non si modifica a mano (vedi pipeline/detail.html).
    """
    if request_item is None or not request_item.quotes:
        return
    latest = max(request_item.quotes, key=lambda q: q.id)
    request_item.value_cents = compute_totals(
        latest.lines, latest.discount_percent, latest.vat_percent
    ).total_cents


def render_body(request: Request, quote: Quote, error: str | None = None):
    context = {
        "quote": quote,
        "totals": compute_totals(quote.lines, quote.discount_percent, quote.vat_percent),
        "error": error,
    }
    return templates.TemplateResponse(request, "quotes/_body.html", context)


@router.get("")
def quote_list(request: Request, db: DbSession, user: CurrentUser):
    quotes = db.scalars(
        select(Quote)
        .options(
            selectinload(Quote.lines),
            joinedload(Quote.customer),
            joinedload(Quote.request).joinedload(PipelineRequest.customer),
        )
        .where(Quote.business_id == user.business_id)
        .order_by(Quote.id.desc())
    ).all()
    rows = [
        (q, compute_totals(q.lines, q.discount_percent, q.vat_percent)) for q in quotes
    ]
    return templates.TemplateResponse(request, "quotes/list.html", {"user": user, "rows": rows})


@router.post("")
def new_quote(db: DbSession, user: CurrentUser):
    quote = Quote(business_id=user.business_id, title="Nuovo preventivo")
    db.add(quote)
    db.commit()
    return RedirectResponse(f"/preventivi/{quote.id}", status_code=303)


@router.get("/{quote_id}")
def quote_editor(request: Request, db: DbSession, user: CurrentUser, quote_id: int):
    quote = get_quote(db, user, quote_id)
    context = {
        "user": user,
        "quote": quote,
        "customers": business_customers(db, user),
        "totals": compute_totals(quote.lines, quote.discount_percent, quote.vat_percent),
        "error": None,
    }
    return templates.TemplateResponse(request, "quotes/editor.html", context)


@router.post("/{quote_id}/intestazione")
def update_header(
    request: Request,
    db: DbSession,
    user: CurrentUser,
    quote_id: int,
    title: Annotated[str, Form()] = "",
    customer_id: Annotated[str, Form()] = "",
    discount_percent: Annotated[str, Form()] = "0",
    vat_percent: Annotated[str, Form()] = "22",
):
    quote = get_quote(db, user, quote_id)
    title = title.strip()
    if not title or len(title) > 150:
        return render_body(request, quote, "Il titolo serve, al massimo di 150 caratteri.")
    try:
        discount = parse_percent(discount_percent)
        vat = parse_percent(vat_percent)
    except ValueError:
        return render_body(request, quote, "Sconto e IVA vanno da 0 a 100.")
    quote.title = title
    quote.customer_id = owned_customer_id(db, user, customer_id)
    quote.discount_percent = discount
    quote.vat_percent = vat
    sync_request_value(quote.request)
    db.commit()
    return render_body(request, quote)


@router.post("/{quote_id}/righe")
def add_line(
    request: Request,
    db: DbSession,
    user: CurrentUser,
    quote_id: int,
    description: Annotated[str, Form()] = "",
    quantity: Annotated[str, Form()] = "1",
    price: Annotated[str, Form()] = "",
    cost: Annotated[str, Form()] = "",
):
    quote = get_quote(db, user, quote_id)
    description = description.strip()
    if not description or len(description) > 200:
        return render_body(request, quote, "Scrivi una descrizione (massimo 200 caratteri).")
    if len(quote.lines) >= MAX_LINES:
        return render_body(request, quote, f"Un preventivo può avere al massimo {MAX_LINES} righe.")
    try:
        qty = parse_quantity(quantity)
        price_cents = parse_euro(price)
        cost_cents = parse_euro(cost)
    except ValueError:
        return render_body(request, quote, "Controlla quantità, prezzo e costo. Esempio: 1,5 e 30,00")
    quote.lines.append(
        QuoteLine(
            description=description,
            quantity=qty,
            unit_price_cents=price_cents,
            unit_cost_cents=cost_cents,
        )
    )
    sync_request_value(quote.request)
    db.commit()
    db.refresh(quote)
    return render_body(request, quote)


@router.post("/{quote_id}/righe/{line_id}/elimina")
def delete_line(request: Request, db: DbSession, user: CurrentUser, quote_id: int, line_id: int):
    quote = get_quote(db, user, quote_id)
    line = next((line for line in quote.lines if line.id == line_id), None)
    if line is None:
        raise HTTPException(status_code=404, detail="Riga non trovata")
    quote.lines.remove(line)
    sync_request_value(quote.request)
    db.commit()
    return render_body(request, quote)


@router.get("/{quote_id}/stampa")
def print_quote(request: Request, db: DbSession, user: CurrentUser, quote_id: int):
    """Versione per il cliente: niente costi né margine."""
    quote = get_quote(db, user, quote_id)
    context = {
        "user": user,
        "quote": quote,
        "totals": compute_totals(quote.lines, quote.discount_percent, quote.vat_percent),
    }
    return templates.TemplateResponse(request, "quotes/print.html", context)


@router.post("/{quote_id}/elimina")
def delete_quote(request: Request, db: DbSession, user: CurrentUser, quote_id: int):
    quote = get_quote(db, user, quote_id)
    request_item = quote.request
    db.delete(quote)
    db.flush()
    if request_item is not None:
        db.refresh(request_item)
        sync_request_value(request_item)
    db.commit()
    if request.headers.get("HX-Request") == "true":
        return Response(headers={"HX-Redirect": "/preventivi"})
    return RedirectResponse("/preventivi", status_code=303)
