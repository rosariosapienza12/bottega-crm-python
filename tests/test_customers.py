from datetime import date, timedelta

from sqlalchemy import select

from app.models import Appointment, Customer, Visit
from tests.conftest import register

MARIA = {
    "first_name": "Maria",
    "last_name": "Rossi",
    "phone": "333 123 4567",
    "email": "",
    "birth_date": "1990-05-12",
    "notes": "Allergica all'ammoniaca",
}


def add_customer(client, **changes):
    response = client.post("/clienti/nuovo", data={**MARIA, **changes}, follow_redirects=False)
    assert response.status_code == 303, response.text
    return response.headers["location"]  # /clienti/<id>


def test_create_customer(logged_in, db):
    url = add_customer(logged_in)

    customer = db.scalars(select(Customer)).one()
    assert url == f"/clienti/{customer.id}"
    assert customer.phone == "+393331234567"
    assert customer.birth_date == date(1990, 5, 12)
    page = logged_in.get(url)
    assert "Maria Rossi" in page.text
    assert "wa.me/393331234567" in page.text


def test_create_customer_shows_errors(logged_in, db):
    response = logged_in.post(
        "/clienti/nuovo", data={**MARIA, "first_name": " ", "phone": "abc"}
    )

    assert response.status_code == 400
    assert "Manca il nome." in response.text
    assert "Numero non valido" in response.text
    assert db.scalars(select(Customer)).first() is None


def test_birth_date_in_the_future_is_rejected(logged_in):
    tomorrow = (date.today() + timedelta(days=1)).isoformat()
    response = logged_in.post("/clienti/nuovo", data={**MARIA, "birth_date": tomorrow})

    assert response.status_code == 400
    assert "nel futuro" in response.text


def test_live_search_returns_only_matching_rows(logged_in):
    add_customer(logged_in)
    add_customer(logged_in, first_name="Luca", last_name="Bianchi", phone="3471112222")

    response = logged_in.get("/clienti", params={"q": "ros"}, headers={"HX-Request": "true"})

    assert "<html" not in response.text  # solo le righe della tabella
    assert "Rossi" in response.text
    assert "Bianchi" not in response.text


def test_edit_customer(logged_in, db):
    url = add_customer(logged_in)

    logged_in.post(f"{url}/modifica", data={**MARIA, "last_name": "Verdi"})

    assert db.scalars(select(Customer)).one().last_name == "Verdi"


def test_delete_customer_also_deletes_visits(logged_in, db):
    url = add_customer(logged_in)
    logged_in.post(f"{url}/visite", data={"visited_on": date.today().isoformat(), "amount": "20"})

    logged_in.post(f"{url}/elimina")

    assert db.scalars(select(Customer)).first() is None
    assert db.scalars(select(Visit)).first() is None


def test_other_business_cannot_see_or_touch_my_customers(client, db):
    register(client, "Salone Anna", "anna@example.com")
    url = add_customer(client)
    client.post("/esci")

    register(client, "Palestra Fit", "fit@example.com")
    assert client.get(url).status_code == 404
    assert client.get(f"{url}/modifica").status_code == 404
    assert client.post(f"{url}/modifica", data=MARIA).status_code == 404
    assert client.post(f"{url}/elimina").status_code == 404
    assert client.post(f"{url}/visite", data={"visited_on": "2026-01-01"}).status_code == 404
    assert "Rossi" not in client.get("/clienti").text
    assert db.scalars(select(Customer)).one().last_name == "Rossi"


def test_add_visit_with_htmx(logged_in, db):
    url = add_customer(logged_in)

    response = logged_in.post(
        f"{url}/visite",
        data={"visited_on": date.today().isoformat(), "amount": "1.250,50", "note": "Colore"},
        headers={"HX-Request": "true"},
    )

    assert response.text.lstrip().startswith('<section id="visite"')
    assert "1.250,50 €" in response.text
    visit = db.scalars(select(Visit)).one()
    assert visit.amount_cents == 125050
    assert visit.note == "Colore"


def test_add_visit_rejects_bad_amount_and_future_date(logged_in, db):
    url = add_customer(logged_in)
    today = date.today().isoformat()
    tomorrow = (date.today() + timedelta(days=1)).isoformat()

    response = logged_in.post(f"{url}/visite", data={"visited_on": today, "amount": "dieci"})
    assert "Importo non valido" in response.text

    response = logged_in.post(f"{url}/visite", data={"visited_on": tomorrow, "amount": "10"})
    assert "nel futuro" in response.text

    assert db.scalars(select(Visit)).first() is None


def test_delete_visit(logged_in, db):
    url = add_customer(logged_in)
    logged_in.post(f"{url}/visite", data={"visited_on": date.today().isoformat(), "amount": "5"})
    visit_id = db.scalars(select(Visit.id)).one()

    response = logged_in.post(f"{url}/visite/{visit_id}/elimina", headers={"HX-Request": "true"})

    assert "Nessuna visita registrata" in response.text
    assert db.scalars(select(Visit)).first() is None


def test_list_can_be_sorted_by_loyalty(logged_in):
    maria = add_customer(logged_in)
    add_customer(logged_in, first_name="Luca", last_name="Bianchi", phone="3471112222")
    today = date.today().isoformat()
    logged_in.post(f"{maria}/visite", data={"visited_on": today, "amount": "300"})

    by_name = logged_in.get("/clienti", headers={"HX-Request": "true"}).text
    by_loyalty = logged_in.get(
        "/clienti", params={"ordina": "fedelta"}, headers={"HX-Request": "true"}
    ).text

    assert by_name.index("Bianchi") < by_name.index("Rossi")
    assert by_loyalty.index("Rossi") < by_loyalty.index("Bianchi")
    # Il campo nascosto del form si aggiorna con l'ordinamento scelto
    assert 'id="ordina" name="ordina" value="fedelta" hx-swap-oob="true"' in by_loyalty


def test_unknown_sort_falls_back_to_name(logged_in):
    response = logged_in.get("/clienti", params={"ordina": "password"})

    assert response.status_code == 200


def test_edit_notes_inline(logged_in, db):
    url = add_customer(logged_in)

    form = logged_in.get(f"{url}/note/modifica", headers={"HX-Request": "true"})
    assert "<textarea" in form.text

    saved = logged_in.post(f"{url}/note", data={"notes": "  Preferisce il giovedì  "})
    assert "Preferisce il giovedì" in saved.text
    assert db.scalars(select(Customer)).one().notes == "Preferisce il giovedì"


def test_add_appointment_from_customer_page(logged_in, db):
    url = add_customer(logged_in)
    day = (date.today() + timedelta(days=2)).isoformat()

    response = logged_in.post(
        f"{url}/appuntamenti", data={"day": day, "hour": "15:30", "service": "Colore"}
    )

    assert "15:30" in response.text
    assert "Colore" in response.text
    appointment = db.scalars(select(Appointment)).one()
    assert appointment.starts_at.isoformat() == f"{day}T15:30:00"


def test_add_appointment_requires_day_and_hour(logged_in, db):
    url = add_customer(logged_in)

    response = logged_in.post(f"{url}/appuntamenti", data={"day": "", "hour": "15:30"})

    assert "Scegli giorno e ora" in response.text
    assert db.scalars(select(Appointment)).first() is None


def test_too_long_values_are_rejected_by_the_server(logged_in, db):
    response = logged_in.post(
        "/clienti/nuovo", data={**MARIA, "first_name": "A" * 101, "notes": "x" * 5001}
    )

    assert response.status_code == 400
    assert "Massimo 100 caratteri" in response.text
    assert "Massimo 5000 caratteri" in response.text
    assert db.scalars(select(Customer)).first() is None


def test_customer_names_are_escaped(logged_in):
    url = add_customer(logged_in, first_name="<script>alert(1)</script>")

    page = logged_in.get(url).text

    assert "<script>alert(1)</script>" not in page
    assert "&lt;script&gt;" in page
