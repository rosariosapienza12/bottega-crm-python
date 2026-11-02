from datetime import date

from sqlalchemy import select

from app.cash import add_months, change_percent
from app.models import Movement, Product
from tests.test_customers import add_customer


def test_add_months_crosses_years():
    assert add_months(date(2026, 11, 1), 2) == date(2027, 1, 1)
    assert add_months(date(2026, 1, 1), -1) == date(2025, 12, 1)


def test_change_percent():
    assert change_percent(150, 100) == 50
    assert change_percent(50, 100) == -50
    assert change_percent(10, 0) is None


def test_cash_counts_visits_and_manual_movements(logged_in):
    today = date.today().isoformat()
    url = add_customer(logged_in)
    logged_in.post(f"{url}/visite", data={"visited_on": today, "amount": "40"})
    logged_in.post("/cassa", data={"kind": "uscita", "occurred_on": today, "amount": "15,50", "category": "Prodotti"})
    logged_in.post("/cassa", data={"kind": "entrata", "occurred_on": today, "amount": "10", "category": "Buono regalo"})

    page = logged_in.get("/cassa").text
    totals = page.split('aria-label="Totali del mese"')[1].split("</section>")[0]

    assert "50,00 €" in totals  # entrate: 40 visita + 10 buono
    assert "15,50 €" in totals  # uscite
    assert "34,50 €" in totals  # saldo
    assert "Maria Rossi" in page


def test_cash_rejects_wrong_category_and_amount(logged_in, db):
    today = date.today().isoformat()

    r1 = logged_in.post("/cassa", data={"kind": "uscita", "occurred_on": today, "amount": "10", "category": "Buono regalo"})
    r2 = logged_in.post("/cassa", data={"kind": "uscita", "occurred_on": today, "amount": "0", "category": "Affitto"})

    assert r1.status_code == 422 and r2.status_code == 422
    assert db.scalars(select(Movement)).first() is None


def test_cash_other_month_and_broken_parameter(logged_in):
    assert logged_in.get("/cassa", params={"mese": "2025-01"}).status_code == 200
    assert logged_in.get("/cassa", params={"mese": "pippo"}).status_code == 200


def test_delete_movement(logged_in, db):
    logged_in.post("/cassa", data={"kind": "uscita", "occurred_on": date.today().isoformat(), "amount": "5", "category": "Altro"})
    movement_id = db.scalars(select(Movement.id)).one()

    logged_in.post(f"/cassa/{movement_id}/elimina")

    assert db.scalars(select(Movement)).first() is None


def add_product(client, **changes):
    data = {"name": "Tinta 5.0", "unit": "pz", "quantity": "3", "min_quantity": "2", "cost": "7,50", **changes}
    return client.post("/magazzino", data=data)


def test_add_product_and_stock_value(logged_in, db):
    page = add_product(logged_in).text

    assert "Tinta 5.0" in page
    assert "22,50 €" in page  # 3 x 7,50
    assert db.scalars(select(Product)).one().unit_cost_cents == 750


def test_quantity_buttons_and_reorder_warning(logged_in, db):
    add_product(logged_in)
    product_id = db.scalars(select(Product.id)).one()

    response = logged_in.post(f"/magazzino/{product_id}/quantita", data={"delta": "-1"})

    assert response.headers["HX-Trigger"] == "stockChanged"
    assert "da riordinare" in response.text
    assert "Tinta 5.0" in logged_in.get("/panoramica").text.split("Da riordinare</h2>")[1]


def test_quantity_never_goes_below_zero_and_odd_deltas_are_refused(logged_in, db):
    add_product(logged_in, quantity="0")
    product_id = db.scalars(select(Product.id)).one()

    logged_in.post(f"/magazzino/{product_id}/quantita", data={"delta": "-1"})
    refused = logged_in.post(f"/magazzino/{product_id}/quantita", data={"delta": "-999999"})

    product = db.get(Product, product_id)
    db.refresh(product)
    assert product.quantity == 0
    assert refused.status_code == 400


def test_edit_and_delete_product(logged_in, db):
    add_product(logged_in)
    product_id = db.scalars(select(Product.id)).one()

    row = logged_in.post(
        f"/magazzino/{product_id}",
        data={"name": "Tinta 6.0", "unit": "pz", "quantity": "10", "min_quantity": "2", "cost": "8"},
    ).text
    assert "Tinta 6.0" in row

    bad = logged_in.post(f"/magazzino/{product_id}", data={"name": "", "quantity": "x"}).text
    assert "Scrivi il nome" in bad

    logged_in.post(f"/magazzino/{product_id}/elimina")
    db.expire_all()
    assert db.scalars(select(Product)).first() is None


def test_product_with_minimum_zero_never_asks_to_reorder(logged_in, db):
    add_product(logged_in, quantity="0", min_quantity="0")

    product = db.scalars(select(Product)).one()
    assert not product.to_reorder
    assert "Ossigeno" not in logged_in.get("/panoramica").text
    assert db.scalars(select(Product).where(Product.to_reorder)).first() is None
