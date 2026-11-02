"""Magazzino: quantità, scorta minima e avviso di riordino."""

from typing import Annotated

from fastapi import APIRouter, Form, HTTPException, Request
from fastapi.responses import RedirectResponse, Response
from sqlalchemy import case, select, update
from sqlalchemy.orm import Session

from app.deps import CurrentUser, DbSession
from app.models import Product, User
from app.money import parse_euro
from app.templating import templates

router = APIRouter(prefix="/magazzino")

MAX_QUANTITY = 1_000_000


def get_product(db: Session, user: User, product_id: int) -> Product:
    product = db.scalar(
        select(Product).where(Product.id == product_id, Product.business_id == user.business_id)
    )
    if product is None:
        raise HTTPException(status_code=404, detail="Prodotto non trovato")
    return product


def business_products(db: Session, business_id: int) -> list[Product]:
    return db.scalars(
        select(Product).where(Product.business_id == business_id).order_by(Product.name)
    ).all()


def read_product_form(name: str, unit: str, quantity: str, min_quantity: str, cost: str) -> dict:
    name, unit = name.strip(), unit.strip() or "pz"
    if not name or len(name) > 100 or len(unit) > 20:
        raise ValueError("Scrivi il nome del prodotto (massimo 100 caratteri).")
    numbers = (quantity.strip() or "0", min_quantity.strip() or "0")
    if not all(n.isdigit() and int(n) <= MAX_QUANTITY for n in numbers):
        raise ValueError("Quantità e scorta minima sono numeri interi.")
    try:
        cost_cents = parse_euro(cost)
    except ValueError:
        raise ValueError("Costo non valido. Esempio: 7,50") from None
    return {
        "name": name,
        "unit": unit,
        "quantity": int(numbers[0]),
        "min_quantity": int(numbers[1]),
        "unit_cost_cents": cost_cents,
    }


def summary(products: list[Product]) -> dict:
    return {
        "stock_value": sum(p.quantity * p.unit_cost_cents for p in products),
        "to_reorder": sum(1 for p in products if p.to_reorder),
        "count": len(products),
    }


def render_page(request: Request, db: Session, user: User, error=None, status=200):
    products = business_products(db, user.business_id)
    context = {"user": user, "products": products, "error": error, **summary(products)}
    return templates.TemplateResponse(request, "inventory/page.html", context, status_code=status)


def render_row(request: Request, product: Product, editing=False, error=None):
    context = {"product": product, "editing": editing, "error": error}
    return templates.TemplateResponse(request, "inventory/_row.html", context)


@router.get("")
def inventory_page(request: Request, db: DbSession, user: CurrentUser):
    return render_page(request, db, user)


# Prima delle rotte con /{product_id}: "riepilogo" non è un id
@router.get("/riepilogo")
def stock_summary(request: Request, db: DbSession, user: CurrentUser):
    context = summary(business_products(db, user.business_id))
    return templates.TemplateResponse(request, "inventory/_summary.html", context)


@router.post("")
def add_product(
    request: Request,
    db: DbSession,
    user: CurrentUser,
    name: Annotated[str, Form()] = "",
    unit: Annotated[str, Form()] = "pz",
    quantity: Annotated[str, Form()] = "0",
    min_quantity: Annotated[str, Form()] = "0",
    cost: Annotated[str, Form()] = "",
):
    try:
        values = read_product_form(name, unit, quantity, min_quantity, cost)
    except ValueError as exc:
        return render_page(request, db, user, str(exc), status=400)
    db.add(Product(business_id=user.business_id, **values))
    db.commit()
    # Redirect dopo il POST: ricaricando la pagina non si aggiunge un doppione
    return RedirectResponse("/magazzino", status_code=303)


@router.post("/{product_id}/quantita")
def change_quantity(
    request: Request,
    db: DbSession,
    user: CurrentUser,
    product_id: int,
    delta: Annotated[int, Form()],
):
    """I pulsanti − e + accanto alla quantità: ±1 o ±10, mai sotto zero."""
    if delta not in (-10, -1, 1, 10):
        raise HTTPException(status_code=400, detail="Variazione non ammessa")
    product = get_product(db, user, product_id)
    # Il calcolo lo fa il database in un colpo solo: leggere, sommare in Python
    # e riscrivere perderebbe un clic se ne arrivano due nello stesso istante
    new_quantity = Product.quantity + delta
    db.execute(
        update(Product)
        .where(Product.id == product.id)
        .values(
            quantity=case(
                (new_quantity < 0, 0),
                (new_quantity > MAX_QUANTITY, MAX_QUANTITY),
                else_=new_quantity,
            )
        )
    )
    db.commit()
    db.refresh(product)
    # Il conteggio "da riordinare" in cima alla pagina si aggiorna da solo
    response = render_row(request, product)
    response.headers["HX-Trigger"] = "stockChanged"
    return response


@router.get("/{product_id}/modifica")
def edit_row(request: Request, db: DbSession, user: CurrentUser, product_id: int):
    return render_row(request, get_product(db, user, product_id), editing=True)


@router.get("/{product_id}")
def show_row(request: Request, db: DbSession, user: CurrentUser, product_id: int):
    return render_row(request, get_product(db, user, product_id))


@router.post("/{product_id}")
def update_product(
    request: Request,
    db: DbSession,
    user: CurrentUser,
    product_id: int,
    name: Annotated[str, Form()] = "",
    unit: Annotated[str, Form()] = "pz",
    quantity: Annotated[str, Form()] = "0",
    min_quantity: Annotated[str, Form()] = "0",
    cost: Annotated[str, Form()] = "",
):
    product = get_product(db, user, product_id)
    try:
        values = read_product_form(name, unit, quantity, min_quantity, cost)
    except ValueError as exc:
        return render_row(request, product, editing=True, error=str(exc))
    for field, value in values.items():
        setattr(product, field, value)
    db.commit()
    response = render_row(request, product)
    response.headers["HX-Trigger"] = "stockChanged"
    return response


@router.post("/{product_id}/elimina")
def delete_product(db: DbSession, user: CurrentUser, product_id: int):
    db.delete(get_product(db, user, product_id))
    db.commit()
    return Response(headers={"HX-Trigger": "stockChanged"})
