"""Pipeline delle richieste: colonne per fase, con trascinamento."""

import re
from typing import Annotated

from fastapi import APIRouter, Form, HTTPException, Request
from fastapi.responses import RedirectResponse, Response
from sqlalchemy import func, select
from sqlalchemy.orm import Session, joinedload, selectinload

from app.deps import CurrentUser, DbSession
from app.models import Customer, Quote, Request as PipelineRequest, User
from app.models.request import STAGE_KEYS, STAGES
from app.money import parse_euro
from app.templating import templates

router = APIRouter(prefix="/richieste")

OPEN_STAGES = ("nuova", "contattata", "preventivo")


def business_customers(db: Session, user: User) -> list[Customer]:
    return db.scalars(
        select(Customer)
        .where(Customer.business_id == user.business_id)
        .order_by(Customer.last_name, Customer.first_name)
    ).all()


def get_request(db: Session, user: User, request_id: int) -> PipelineRequest:
    item = db.scalar(
        select(PipelineRequest).where(
            PipelineRequest.id == request_id,
            PipelineRequest.business_id == user.business_id,
        )
    )
    if item is None:
        raise HTTPException(status_code=404, detail="Richiesta non trovata")
    return item


# Solo cifre 0-9, al massimo 9: isdigit() accetterebbe anche "²", che poi
# int() rifiuta con un errore 500, e un numero enorme manderebbe in errore il database
PLAIN_ID = re.compile(r"[0-9]{1,9}")


def owned_customer_id(db: Session, user: User, raw: str) -> int | None:
    """L'id del cliente scelto nel form, solo se è di questa attività."""
    raw = raw.strip()
    if not PLAIN_ID.fullmatch(raw):
        return None
    customer_id = int(raw)
    owned = db.scalar(
        select(Customer.id).where(
            Customer.id == customer_id, Customer.business_id == user.business_id
        )
    )
    if owned is None:
        raise HTTPException(status_code=404, detail="Cliente non trovato")
    return customer_id


def board_context(db: Session, user: User, error: str | None = None) -> dict:
    items = db.scalars(
        select(PipelineRequest)
        .options(joinedload(PipelineRequest.customer), selectinload(PipelineRequest.quotes))
        .where(PipelineRequest.business_id == user.business_id)
        .order_by(PipelineRequest.position, PipelineRequest.id)
    ).all()
    columns = []
    for key, label in STAGES:
        cards = [item for item in items if item.stage == key]
        columns.append(
            {"key": key, "label": label, "cards": cards, "total": sum(c.value_cents for c in cards)}
        )
    return {
        "user": user,
        "columns": columns,
        "stages": STAGES,
        "customers": business_customers(db, user),
        "error": error,
    }


def render_board(request: Request, db: Session, user: User, partial: bool, error=None):
    template = "pipeline/_board.html" if partial else "pipeline/board.html"
    status = 422 if error else 200
    return templates.TemplateResponse(
        request, template, board_context(db, user, error), status_code=status
    )


@router.get("")
def board(request: Request, db: DbSession, user: CurrentUser):
    return render_board(request, db, user, partial=False)


class RequestFormError(ValueError):
    pass


def read_request_form(db, user, title, customer_id, contact_name, value, notes) -> dict:
    title = title.strip()
    contact_name = contact_name.strip()
    if not title:
        raise RequestFormError("Scrivi cosa chiede il cliente.")
    if len(title) > 150 or len(contact_name) > 100 or len(notes) > 5000:
        raise RequestFormError("Uno dei campi è troppo lungo.")
    owner = owned_customer_id(db, user, customer_id)
    if owner is None and not contact_name:
        raise RequestFormError("Scegli un cliente o scrivi il nome di chi ha chiesto.")
    try:
        cents = parse_euro(value)
    except ValueError:
        raise RequestFormError("Valore non valido. Esempio: 150 oppure 150,50") from None
    return {
        "title": title,
        "customer_id": owner,
        "contact_name": None if owner else contact_name,
        "value_cents": cents,
        "notes": notes.strip() or None,
    }


@router.post("")
def create_request(
    request: Request,
    db: DbSession,
    user: CurrentUser,
    title: Annotated[str, Form()] = "",
    customer_id: Annotated[str, Form()] = "",
    contact_name: Annotated[str, Form()] = "",
    value: Annotated[str, Form()] = "",
):
    try:
        values = read_request_form(db, user, title, customer_id, contact_name, value, "")
    except RequestFormError as exc:
        return render_board(request, db, user, partial=True, error=str(exc))
    last = db.scalar(
        select(func.max(PipelineRequest.position)).where(
            PipelineRequest.business_id == user.business_id, PipelineRequest.stage == "nuova"
        )
    )
    db.add(PipelineRequest(business_id=user.business_id, position=(last or 0) + 1, **values))
    db.commit()
    return render_board(request, db, user, partial=True)


@router.post("/{request_id}/sposta")
def move_request(
    request: Request,
    db: DbSession,
    user: CurrentUser,
    request_id: int,
    stage: Annotated[str, Form()],
    order: Annotated[str, Form()] = "",
):
    """Sposta una richiesta in un'altra colonna.

    `order` sono gli id della colonna di arrivo nell'ordine in cui li vede
    l'utente dopo il trascinamento, separati da virgole. Dal menu a tendina
    (telefono, tastiera) arriva vuoto: la richiesta va in fondo.
    """
    if stage not in STAGE_KEYS:
        raise HTTPException(status_code=400, detail="Fase sconosciuta")
    item = get_request(db, user, request_id)
    item.stage = stage

    ids = [int(part) for part in order.split(",") if PLAIN_ID.fullmatch(part.strip())][:500]
    if item.id not in ids:
        ids.append(item.id)
    # Solo le richieste di questa attività: un id estraneo nella lista viene ignorato
    column = {
        r.id: r
        for r in db.scalars(
            select(PipelineRequest).where(
                PipelineRequest.business_id == user.business_id, PipelineRequest.id.in_(ids)
            )
        )
    }
    for position, request_id_in_order in enumerate(ids, start=1):
        moved = column.get(request_id_in_order)
        if moved is not None and moved.stage == stage:
            moved.position = position
    db.commit()
    return render_board(request, db, user, partial=True)


@router.get("/{request_id}")
def request_detail(request: Request, db: DbSession, user: CurrentUser, request_id: int):
    item = get_request(db, user, request_id)
    context = {
        "user": user,
        "item": item,
        "stages": STAGES,
        "customers": business_customers(db, user),
        "error": None,
    }
    return templates.TemplateResponse(request, "pipeline/detail.html", context)


@router.post("/{request_id}")
def update_request(
    request: Request,
    db: DbSession,
    user: CurrentUser,
    request_id: int,
    title: Annotated[str, Form()] = "",
    customer_id: Annotated[str, Form()] = "",
    contact_name: Annotated[str, Form()] = "",
    value: Annotated[str, Form()] = "",
    stage: Annotated[str, Form()] = "",
    notes: Annotated[str, Form()] = "",
):
    item = get_request(db, user, request_id)
    try:
        values = read_request_form(db, user, title, customer_id, contact_name, value, notes)
        if stage not in STAGE_KEYS:
            raise RequestFormError("Fase sconosciuta.")
    except RequestFormError as exc:
        context = {
            "user": user,
            "item": item,
            "stages": STAGES,
            "customers": business_customers(db, user),
            "error": str(exc),
        }
        return templates.TemplateResponse(request, "pipeline/detail.html", context, status_code=400)
    if item.quotes:
        values.pop("value_cents")
    for field, new_value in values.items():
        setattr(item, field, new_value)
    item.stage = stage
    db.commit()
    return RedirectResponse("/richieste", status_code=303)


@router.post("/{request_id}/elimina")
def delete_request(request: Request, db: DbSession, user: CurrentUser, request_id: int):
    item = get_request(db, user, request_id)
    # I preventivi restano, ma senza la richiesta
    for quote in item.quotes:
        quote.request_id = None
    db.delete(item)
    db.commit()
    if request.headers.get("HX-Request") == "true":
        return Response(headers={"HX-Redirect": "/richieste"})
    return RedirectResponse("/richieste", status_code=303)


@router.post("/{request_id}/preventivo")
def quote_from_request(db: DbSession, user: CurrentUser, request_id: int):
    """Crea un preventivo già collegato alla richiesta e al cliente."""
    item = get_request(db, user, request_id)
    if item.quotes:
        latest = max(item.quotes, key=lambda q: q.id)
        return RedirectResponse(f"/preventivi/{latest.id}", status_code=303)
    quote = Quote(
        business_id=user.business_id,
        request=item,
        customer_id=item.customer_id,
        title=item.title,
    )
    db.add(quote)
    db.commit()
    return RedirectResponse(f"/preventivi/{quote.id}", status_code=303)


def open_requests(db: Session, business_id: int) -> tuple[int, int]:
    """Quante richieste sono ancora aperte e quanto valgono in tutto."""
    count, cents = db.execute(
        select(func.count(PipelineRequest.id), func.coalesce(func.sum(PipelineRequest.value_cents), 0))
        .where(
            PipelineRequest.business_id == business_id,
            PipelineRequest.stage.in_(OPEN_STAGES),
        )
    ).one()
    return count, cents
