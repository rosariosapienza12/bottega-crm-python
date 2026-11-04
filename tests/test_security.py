"""Test "da attaccante": cosa succede se qualcuno prova a forzare l'app."""

from datetime import date

import pytest
from sqlalchemy import select

from app.models import Movement, Product, Quote, Request as PipelineRequest
from tests.conftest import PASSWORD, register
from tests.test_customers import add_customer


def test_login_is_blocked_after_too_many_wrong_passwords(client):
    register(client)
    client.post("/esci")

    for _ in range(5):
        client.post("/accedi", data={"email": "anna@example.com", "password": "sbagliata"})
    blocked = client.post("/accedi", data={"email": "anna@example.com", "password": PASSWORD})

    # Bloccato anche con la password giusta: chi tira a indovinare non sa quando ha indovinato
    assert blocked.status_code == 429
    assert "Troppi tentativi" in blocked.text


def test_cookie_copied_before_logout_stops_working(client):
    register(client)
    stolen = client.cookies.get("bottega_session")

    client.post("/esci")
    client.cookies.set("bottega_session", stolen)

    response = client.get("/panoramica", follow_redirects=False)
    assert response.status_code == 303
    assert response.headers["location"] == "/accedi"


def test_tampered_cookie_is_rejected(client):
    register(client)
    cookie = client.cookies.get("bottega_session")
    client.cookies.set("bottega_session", cookie[:-4] + "AAAA")

    assert client.get("/panoramica", follow_redirects=False).status_code == 303


def test_post_from_another_site_is_blocked(logged_in):
    response = logged_in.post(
        "/cassa",
        data={"kind": "uscita", "occurred_on": "2026-01-01", "amount": "1", "category": "Altro"},
        headers={"Origin": "https://sito-cattivo.example"},
    )
    assert response.status_code == 403


def test_post_from_our_own_page_passes(logged_in):
    response = logged_in.post("/preventivi", headers={"Origin": "http://testserver"}, follow_redirects=False)
    assert response.status_code == 303


def test_script_in_a_request_title_is_not_executed(logged_in):
    logged_in.post("/richieste", data={"title": "<img src=x onerror=alert(1)>", "contact_name": "X"})

    page = logged_in.get("/richieste").text

    assert "<img src=x" not in page
    assert "&lt;img src=x" in page


def test_security_headers(client):
    headers = client.get("/").headers
    # Script solo dal nostro sito: nessun CDN, niente script inline
    assert "script-src 'self';" in headers["Content-Security-Policy"]
    assert "cdn.jsdelivr.net" not in headers["Content-Security-Policy"]
    assert headers["X-Frame-Options"] == "DENY"


def test_libraries_are_served_by_the_site(client):
    page = client.get("/").text

    for path in ("/static/vendor/tailwindcss-browser-4.1.11.js", "/static/vendor/htmx-2.0.4.min.js"):
        assert f'src="{path}"' in page
        assert client.get(path).status_code == 200
    assert "cdn.jsdelivr.net" not in page


@pytest.fixture
def two_businesses(client, db):
    """Anna crea un po' di tutto, poi esce. Entra la palestra, che non deve vedere niente."""
    register(client, "Salone Anna", "anna@example.com")
    add_customer(client)
    client.post("/richieste", data={"title": "Segreto di Anna", "contact_name": "Sara"})
    client.post("/preventivi")
    client.post("/cassa", data={"kind": "uscita", "occurred_on": date.today().isoformat(), "amount": "9", "category": "Altro"})
    client.post("/magazzino", data={"name": "Tinta di Anna", "quantity": "1"})
    ids = {
        "request": db.scalars(select(PipelineRequest.id)).one(),
        "quote": db.scalars(select(Quote.id)).one(),
        "movement": db.scalars(select(Movement.id)).one(),
        "product": db.scalars(select(Product.id)).one(),
    }
    client.post("/esci")
    register(client, "Palestra Fit", "fit@example.com")
    return ids


def test_other_business_cannot_reach_anything_by_id(client, two_businesses):
    ids = two_businesses
    attempts = [
        ("get", f"/richieste/{ids['request']}"),
        ("post", f"/richieste/{ids['request']}/sposta"),
        ("post", f"/richieste/{ids['request']}/elimina"),
        ("post", f"/richieste/{ids['request']}/preventivo"),
        ("get", f"/preventivi/{ids['quote']}"),
        ("get", f"/preventivi/{ids['quote']}/stampa"),
        ("post", f"/preventivi/{ids['quote']}/righe"),
        ("post", f"/preventivi/{ids['quote']}/elimina"),
        ("post", f"/cassa/{ids['movement']}/elimina"),
        ("post", f"/magazzino/{ids['product']}/quantita"),
        ("get", f"/magazzino/{ids['product']}/modifica"),
        ("post", f"/magazzino/{ids['product']}/elimina"),
    ]
    for method, url in attempts:
        data = {"stage": "persa", "delta": "1", "description": "x", "price": "1"} if method == "post" else None
        response = getattr(client, method)(url, data=data) if data else getattr(client, method)(url)
        assert response.status_code == 404, url


def test_other_business_lists_show_nothing_of_anna(client, two_businesses):
    for page in ["/richieste", "/preventivi", "/cassa", "/magazzino", "/panoramica", "/clienti"]:
        text = client.get(page).text
        assert "Segreto di Anna" not in text, page
        assert "Tinta di Anna" not in text, page
        assert "Maria Rossi" not in text, page


def test_cannot_attach_someone_elses_customer(client, db, two_businesses):
    anna_customer = 1
    response = client.post("/richieste", data={"title": "Furbo", "customer_id": str(anna_customer)})
    assert response.status_code == 404


def test_dragging_cannot_reorder_someone_elses_requests(client, db, two_businesses):
    client.post("/richieste", data={"title": "Mia", "contact_name": "Io"})
    mine = db.scalars(select(PipelineRequest).where(PipelineRequest.title == "Mia")).one()
    theirs = db.get(PipelineRequest, two_businesses["request"])
    before = (theirs.stage, theirs.position)

    client.post(f"/richieste/{mine.id}/sposta", data={"stage": "nuova", "order": f"{theirs.id},{mine.id}"})

    db.refresh(theirs)
    assert (theirs.stage, theirs.position) == before


def test_a_stranger_cannot_lock_out_my_account(client):
    register(client)
    client.post("/esci")
    # Cinque password sbagliate da un altro computer (altro IP)...
    from app.ratelimit import login_limiter
    for _ in range(5):
        login_limiter.record("ip:1.2.3.4|email:anna@example.com")

    # ...ma dal mio entro lo stesso
    response = client.post("/accedi", data={"email": "anna@example.com", "password": PASSWORD})
    assert response.status_code == 200
    assert "Panoramica" in response.text


def test_mass_registration_is_limited(client):
    for i in range(10):
        client.post("/registrati", data={"business_name": f"Bot {i}", "email": f"bot{i}@example.com", "password": PASSWORD})
        client.post("/esci")
    response = client.post("/registrati", data={"business_name": "Bot", "email": "bot99@example.com", "password": PASSWORD})
    assert response.status_code == 429


def test_private_pages_are_not_cached(logged_in):
    assert logged_in.get("/panoramica").headers["Cache-Control"] == "no-store"


@pytest.mark.parametrize("url", ["/cassa?mese=9999-12", "/agenda?settimana=9999-12-31", "/cassa?mese=0001-01"])
def test_absurd_dates_in_the_address_do_not_crash(logged_in, url):
    assert logged_in.get(url).status_code == 200


def test_absurd_date_in_a_form_is_rejected_before_saving(logged_in, db):
    response = logged_in.post(
        "/cassa", data={"kind": "uscita", "occurred_on": "9999-12-31", "amount": "5", "category": "Altro"}
    )
    assert response.status_code == 422
    assert db.scalars(select(Movement)).first() is None


# --- Configurazione e input strani ---


@pytest.mark.parametrize("weak_key", ["corta", "cambiami-con-una-stringa-casuale"])
def test_app_refuses_a_weak_or_example_secret_key(weak_key):
    from pydantic import ValidationError

    from app.config import Settings

    # Con la chiave d'esempio (pubblica su GitHub) chiunque firmerebbe cookie finti
    with pytest.raises(ValidationError, match="SECRET_KEY"):
        Settings(database_url="sqlite://", secret_key=weak_key)


def test_demo_script_refuses_a_production_database():
    from scripts.crea_demo import check_local_database

    check_local_database("sqlite:///bottega.db")  # in locale va bene
    with pytest.raises(SystemExit):
        check_local_database("postgresql://utente@server/bottega")


@pytest.mark.parametrize("strange_id", ["²", "9" * 30, "-1", "1e3"])
def test_strange_customer_id_in_a_form_is_ignored(logged_in, db, strange_id):
    # "²" passa isdigit() ma int() lo rifiuta: prima diventava un errore 500
    response = logged_in.post(
        "/richieste",
        data={"title": "Colore", "contact_name": "Sara", "value": "100", "customer_id": strange_id},
        headers={"HX-Request": "true"},
    )

    assert response.status_code == 200
    item = db.scalars(select(PipelineRequest)).one()
    assert item.customer_id is None


def test_strange_quantity_in_stock_is_refused(logged_in, db):
    response = logged_in.post(
        "/magazzino",
        data={"name": "Tinta", "unit": "pz", "quantity": "²", "min_quantity": "0", "cost": "1"},
    )

    assert response.status_code != 500
    assert db.scalars(select(Product)).first() is None


@pytest.mark.parametrize(
    "url",
    ["postgresql://u:p@db.example.com/crm?sslmode=require", "postgres://u:p@db.example.com/crm?sslmode=require"],
)
def test_postgres_urls_use_psycopg_driver(url):
    from app.config import Settings

    settings = Settings(database_url=url, secret_key="x" * 32)

    assert settings.database_url == "postgresql+psycopg://u:p@db.example.com/crm?sslmode=require"
