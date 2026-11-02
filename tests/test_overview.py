from datetime import date, timedelta

from app.insights import next_birthday
from tests.test_customers import add_customer


def test_dormant_customer_is_listed_with_whatsapp_link(logged_in):
    old = (date.today() - timedelta(days=90)).isoformat()
    recent = date.today().isoformat()
    maria = add_customer(logged_in)
    luca = add_customer(logged_in, first_name="Luca", last_name="Bianchi", phone="3471112222")
    logged_in.post(f"{maria}/visite", data={"visited_on": old, "amount": "30"})
    logged_in.post(f"{luca}/visite", data={"visited_on": recent, "amount": "20"})

    page = logged_in.get("/panoramica").text
    to_contact = page.split("Da ricontattare")[1].split("Compleanni")[0]

    assert "Maria Rossi" in to_contact
    assert "90 giorni fa" in to_contact
    assert "wa.me/393331234567" in to_contact
    assert "Luca Bianchi" not in to_contact


def test_month_totals(logged_in):
    url = add_customer(logged_in)
    logged_in.post(f"{url}/visite", data={"visited_on": date.today().isoformat(), "amount": "25,50"})

    page = logged_in.get("/panoramica").text
    strip = page.split('aria-label="Numeri del mese"')[1].split("</section>")[0]

    # L'incasso del mese è nella striscia in alto, colorato come "soldi"
    assert '<div class="value money">25,50 €</div>' in strip


def test_upcoming_birthday_is_listed(logged_in):
    soon = date.today() + timedelta(days=3)
    birth = date(1990, soon.month, soon.day) if (soon.month, soon.day) != (2, 29) else date(1992, 2, 29)
    add_customer(logged_in, birth_date=birth.isoformat())

    page = logged_in.get("/panoramica").text
    birthdays = page.split("Compleanni")[1]

    assert "Maria Rossi" in birthdays
    assert "tra 3 giorni" in birthdays or "domani" in birthdays or "oggi" in birthdays


def test_next_birthday():
    today = date(2026, 11, 2)
    assert next_birthday(date(1990, 11, 2), today) == date(2026, 11, 2)
    assert next_birthday(date(1990, 11, 10), today) == date(2026, 11, 10)
    assert next_birthday(date(1990, 1, 5), today) == date(2027, 1, 5)
    # 29 febbraio in un anno non bisestile: si festeggia il 1° marzo
    assert next_birthday(date(2000, 2, 29), date(2027, 2, 1)) == date(2027, 3, 1)
