from decimal import Decimal
from types import SimpleNamespace

import pytest
from sqlalchemy import select

from app.models import Quote, Request as PipelineRequest
from app.quotes import compute_totals, parse_percent, parse_quantity
from tests.test_customers import add_customer


def line(quantity, price, cost=0):
    return SimpleNamespace(quantity=Decimal(quantity), unit_price_cents=price, unit_cost_cents=cost)


def test_totals_with_discount_and_vat():
    totals = compute_totals([line("2", 50_00, 15_00), line("1.5", 30_00)], 10, 22)

    assert totals.subtotal_cents == 145_00
    assert totals.discount_cents == 14_50
    assert totals.taxable_cents == 130_50
    assert totals.vat_cents == 28_71
    assert totals.total_cents == 159_21
    assert totals.cost_cents == 30_00
    assert totals.margin_cents == 100_50
    assert totals.margin_percent == 77


def test_half_cents_round_up_like_a_shop_does():
    # 0,5 centesimi: round() di Python andrebbe al pari (giù), qui si va su
    totals = compute_totals([line("1", 25)], 0, 10)
    assert totals.vat_cents == 3


def test_subtotal_is_the_sum_of_the_rounded_lines():
    lines = [line("0.33", 1_00), line("0.33", 1_00), line("0.33", 1_00)]
    totals = compute_totals(lines, 0, 0)
    assert totals.subtotal_cents == 3 * 33


def test_empty_quote_has_no_margin_percent():
    totals = compute_totals([], 0, 22)
    assert totals.total_cents == 0
    assert totals.margin_percent is None


@pytest.mark.parametrize("raw, expected", [("1", "1"), ("1,5", "1.5"), ("", "1"), ("0.25", "0.25")])
def test_parse_quantity(raw, expected):
    assert parse_quantity(raw) == Decimal(expected)


@pytest.mark.parametrize("raw", ["0", "-1", "abc", "1,555", "10000", "NaN", "Infinity"])
def test_parse_quantity_rejects(raw):
    with pytest.raises(ValueError):
        parse_quantity(raw)


def test_parse_percent():
    assert parse_percent("22") == 22
    assert parse_percent("10%") == 10
    for bad in ["-5", "101", "abc", "2.5"]:
        with pytest.raises(ValueError):
            parse_percent(bad)


def new_quote(client):
    response = client.post("/preventivi", follow_redirects=False)
    return response.headers["location"]


def test_build_a_quote(logged_in, db):
    url = new_quote(logged_in)

    logged_in.post(f"{url}/intestazione", data={"title": "Sposa", "discount_percent": "0", "vat_percent": "22"})
    body = logged_in.post(
        f"{url}/righe", data={"description": "Trucco sposa", "quantity": "1", "price": "150", "cost": "20"}
    ).text

    assert "Trucco sposa" in body
    assert "183,00 €" in body  # 150 + 22% IVA
    quote = db.scalars(select(Quote)).one()
    assert quote.title == "Sposa"
    assert len(quote.lines) == 1


def test_bad_line_shows_error_and_adds_nothing(logged_in, db):
    url = new_quote(logged_in)

    body = logged_in.post(f"{url}/righe", data={"description": "X", "quantity": "-1", "price": "10"}).text

    assert "Controlla quantità" in body
    assert db.scalars(select(Quote)).one().lines == []


def test_print_version_hides_costs(logged_in):
    url = new_quote(logged_in)
    logged_in.post(f"{url}/righe", data={"description": "Piega", "price": "30", "cost": "12,34"})

    page = logged_in.get(f"{url}/stampa").text

    assert "Piega" in page
    assert "12,34" not in page
    assert "Margine" not in page and "margine" not in page


def test_delete_line(logged_in, db):
    url = new_quote(logged_in)
    logged_in.post(f"{url}/righe", data={"description": "Piega", "price": "30"})
    line_id = db.scalars(select(Quote)).one().lines[0].id

    logged_in.post(f"{url}/righe/{line_id}/elimina")

    assert db.scalars(select(Quote)).one().lines == []


def test_quote_from_request_keeps_pipeline_value_in_sync(logged_in, db):
    customer_url = add_customer(logged_in)
    customer_id = int(customer_url.rsplit("/", 1)[1])
    logged_in.post("/richieste", data={"title": "Colore", "customer_id": str(customer_id)})
    request_id = db.scalars(select(PipelineRequest.id)).one()

    url = logged_in.post(f"/richieste/{request_id}/preventivo", follow_redirects=False).headers["location"]
    logged_in.post(f"{url}/righe", data={"description": "Colore", "price": "100"})

    item = db.scalars(select(PipelineRequest)).one()
    db.refresh(item)
    assert item.value_cents == 122_00
    assert db.scalars(select(Quote)).one().customer_id == customer_id


def test_delete_quote(logged_in, db):
    url = new_quote(logged_in)
    logged_in.post(f"{url}/elimina")
    assert db.scalars(select(Quote)).first() is None


def test_request_value_follows_its_quote_and_cannot_be_overwritten(logged_in, db):
    logged_in.post("/richieste", data={"title": "Colore", "contact_name": "Sara", "value": "50"})
    request_id = db.scalars(select(PipelineRequest.id)).one()
    url = logged_in.post(f"/richieste/{request_id}/preventivo", follow_redirects=False).headers["location"]
    logged_in.post(f"{url}/righe", data={"description": "Colore", "price": "100", "quantity": "1"})

    # Un secondo clic su "preventivo" riapre lo stesso, non ne crea un altro
    again = logged_in.post(f"/richieste/{request_id}/preventivo", follow_redirects=False).headers["location"]
    assert again == url
    assert len(db.scalars(select(Quote)).all()) == 1

    # Il valore scritto a mano viene ignorato finché c'è il preventivo
    logged_in.post(
        f"/richieste/{request_id}",
        data={"title": "Colore", "contact_name": "Sara", "value": "1", "stage": "nuova", "notes": ""},
    )
    item = db.get(PipelineRequest, request_id)
    db.refresh(item)
    assert item.value_cents == 122_00
