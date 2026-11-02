from datetime import date, datetime, timedelta

from sqlalchemy import select

from app.models import Appointment, Visit
from tests.conftest import register
from tests.test_customers import add_customer


def customer_id(url):
    return int(url.rsplit("/", 1)[1])


def add_appointment(client, url, starts_at, service="Taglio"):
    client.post(
        f"{url}/appuntamenti",
        data={"day": starts_at.date().isoformat(), "hour": starts_at.strftime("%H:%M"), "service": service},
    )


def test_agenda_shows_the_week(logged_in):
    url = add_customer(logged_in)
    monday = date.today() - timedelta(days=date.today().weekday())
    add_appointment(logged_in, url, datetime.combine(monday, datetime.min.time()).replace(hour=10))

    page = logged_in.get("/agenda").text

    assert "Lunedì" in page and "Domenica" in page
    assert "10:00" in page
    assert "Maria Rossi" in page


def test_agenda_other_week(logged_in):
    url = add_customer(logged_in)
    next_week = date.today() + timedelta(days=7)
    starts_at = datetime.combine(next_week, datetime.min.time()).replace(hour=9)
    add_appointment(logged_in, url, starts_at, service="Permanente")

    this_week = logged_in.get("/agenda").text
    that_week = logged_in.get("/agenda", params={"settimana": next_week.isoformat()}).text

    assert "Permanente" not in this_week
    assert "Permanente" in that_week


def test_agenda_ignores_a_broken_week_parameter(logged_in):
    assert logged_in.get("/agenda", params={"settimana": "ieri"}).status_code == 200


def test_add_appointment_from_agenda(logged_in, db):
    url = add_customer(logged_in)
    day = date.today() + timedelta(days=1)

    response = logged_in.post(
        "/agenda",
        data={"customer_id": customer_id(url), "day": day.isoformat(), "hour": "11:15", "service": "Piega"},
    )

    assert "11:15" in response.text
    assert db.scalars(select(Appointment)).one().service == "Piega"


def test_done_turns_appointment_into_visit(logged_in, db):
    url = add_customer(logged_in)
    add_appointment(logged_in, url, datetime.now() - timedelta(hours=1), service="Colore")
    appointment_id = db.scalars(select(Appointment.id)).one()

    response = logged_in.post(f"/appuntamenti/{appointment_id}/fatto", data={"amount": "45,50"})

    assert response.headers["HX-Trigger"] == "visitsChanged"
    assert db.scalars(select(Appointment)).first() is None
    visit = db.scalars(select(Visit)).one()
    assert visit.amount_cents == 4550
    assert visit.note == "Colore"


def test_future_appointment_cannot_be_marked_done(logged_in, db):
    url = add_customer(logged_in)
    add_appointment(logged_in, url, datetime.now() + timedelta(days=1))
    appointment_id = db.scalars(select(Appointment.id)).one()

    response = logged_in.post(f"/appuntamenti/{appointment_id}/fatto", data={"amount": "10"})

    assert response.status_code == 400
    assert db.scalars(select(Visit)).first() is None


def test_done_with_bad_amount_changes_nothing(logged_in, db):
    url = add_customer(logged_in)
    add_appointment(logged_in, url, datetime.now() - timedelta(hours=1))
    appointment_id = db.scalars(select(Appointment.id)).one()

    response = logged_in.post(f"/appuntamenti/{appointment_id}/fatto", data={"amount": "tanti"})

    # 400 e non 422: htmx non deve toccare la riga (con 422 la cancellerebbe)
    assert response.status_code == 400
    assert db.scalars(select(Appointment)).first() is not None
    assert db.scalars(select(Visit)).first() is None


def test_cancel_appointment(logged_in, db):
    url = add_customer(logged_in)
    add_appointment(logged_in, url, datetime.now() + timedelta(days=1))
    appointment_id = db.scalars(select(Appointment.id)).one()

    logged_in.post(f"/appuntamenti/{appointment_id}/annulla")

    assert db.scalars(select(Appointment)).first() is None


def test_other_business_cannot_touch_my_appointments(client, db):
    register(client, "Salone Anna", "anna@example.com")
    url = add_customer(client)
    add_appointment(client, url, datetime.now() - timedelta(hours=1))
    appointment_id = db.scalars(select(Appointment.id)).one()
    client.post("/esci")

    register(client, "Palestra Fit", "fit@example.com")
    assert client.post(f"/appuntamenti/{appointment_id}/fatto", data={"amount": "1"}).status_code == 404
    assert client.post(f"/appuntamenti/{appointment_id}/annulla").status_code == 404
    response = client.post(
        "/agenda",
        data={"customer_id": customer_id(url), "day": date.today().isoformat(), "hour": "10:00"},
    )
    assert response.status_code == 404
    assert "Maria Rossi" not in client.get("/agenda").text
    assert db.scalars(select(Appointment)).one() is not None


def test_today_appointments_on_overview(logged_in):
    url = add_customer(logged_in)
    now = datetime.now()
    # Non a cavallo della mezzanotte, altrimenti finisce domani
    starts_at = now.replace(hour=23, minute=0) if now.hour < 23 else now.replace(minute=0)
    add_appointment(logged_in, url, starts_at, service="Taglio")

    page = logged_in.get("/panoramica").text
    today_section = page.split("<h2>Oggi</h2>")[1].split("Da ricontattare")[0]

    assert "Maria Rossi" in today_section
    assert starts_at.strftime("%H:%M") in today_section
