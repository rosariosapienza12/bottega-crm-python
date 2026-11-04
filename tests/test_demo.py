"""Demo online: ogni visitatore riceve un'attività di prova tutta sua, che dura 24 ore."""

import sqlite3
from datetime import timedelta

import pytest
from sqlalchemy import select

from app.config import settings
from app.demo import DEMO_DOMAIN, create_demo_account, is_demo_email, purge_expired_demos, utc_now
from app.models import Business, Customer, User
from app.routes.auth import client_ip
from tests.conftest import register


@pytest.fixture
def demo_on(monkeypatch):
    monkeypatch.setattr(settings, "demo_mode", True)


def test_without_demo_mode_there_is_no_demo(client, db):
    # Sull'app vera nessuno deve poter creare attività o entrare senza password
    assert client.post("/demo").status_code == 404
    assert "Prova la demo" not in client.get("/accedi").text
    assert db.scalars(select(Business)).first() is None


def test_each_visitor_gets_a_private_demo_business(client, db, demo_on):
    page = client.get("/")
    assert "Prova la demo" in page.text
    assert "si cancellano dopo 24 ore" in page.text

    response = client.post("/demo", follow_redirects=False)
    assert response.headers["location"] == "/panoramica"
    assert "Salone Anna (prova)" in client.get("/panoramica").text

    client.post("/esci")
    client.post("/demo")

    # Due clic, due attività separate, ognuna con i suoi clienti di prova
    demo_users = db.scalars(select(User)).all()
    assert len(demo_users) == 2
    assert all(is_demo_email(u.email) for u in demo_users)
    assert demo_users[0].business_id != demo_users[1].business_id
    for user in demo_users:
        assert db.scalars(select(Customer).where(Customer.business_id == user.business_id)).first()


def test_demo_accounts_cannot_log_in_with_a_password(client, db, demo_on):
    client.post("/demo")
    client.post("/esci")
    email = db.scalars(select(User)).one().email

    # Indirizzo su un dominio .invalid e password casuale che nessuno conosce
    assert email.endswith(f"@{DEMO_DOMAIN}")
    response = client.post("/accedi", data={"email": email, "password": "prova-bottega-2026"})
    assert response.status_code == 400


def test_expired_demos_are_deleted_with_all_their_data(client, db):
    old = create_demo_account(db)
    old.created_at = utc_now() - timedelta(hours=25)
    recent = create_demo_account(db)
    register(client)  # un'attività vera, che non va mai toccata
    db.commit()

    assert purge_expired_demos(db) == 1

    remaining = {u.email for u in db.scalars(select(User))}
    assert old.email not in remaining
    assert recent.email in remaining
    assert "anna@example.com" in remaining
    old_customers = db.scalars(select(Customer).where(Customer.business_id == old.business_id)).all()
    assert old_customers == []


def test_too_many_demos_from_one_network_are_refused(client, demo_on):
    for _ in range(10):
        client.post("/demo")
        client.post("/esci")

    assert client.post("/demo").status_code == 429


def test_forwarded_ip_is_used_only_when_trusted(client, monkeypatch):
    class FakeRequest:
        headers = {"x-forwarded-for": "203.0.113.7, 10.0.0.1"}
        client = type("C", (), {"host": "10.0.0.1"})()

    # Di default l'header lo può scrivere chiunque: non ci fidiamo
    assert client_ip(FakeRequest()) == "10.0.0.1"
    monkeypatch.setattr(settings, "trust_forwarded_for", True)
    assert client_ip(FakeRequest()) == "203.0.113.7"


def test_app_can_run_its_own_migrations(tmp_path, monkeypatch):
    from sqlalchemy import create_engine

    from app import database
    from app.migrate import upgrade_database

    path = tmp_path / "nuovo.db"
    monkeypatch.setattr(database, "engine", create_engine(f"sqlite:///{path}"))
    monkeypatch.setattr(database, "is_sqlite", True)

    upgrade_database()

    tables = {row[0] for row in sqlite3.connect(path).execute("select name from sqlite_master where type='table'")}
    assert {"businesses", "users", "customers", "alembic_version"} <= tables


def test_demo_business_has_a_complete_quote(db):
    from app.models import Quote

    user = create_demo_account(db)

    quote = db.scalars(select(Quote).where(Quote.business_id == user.business_id)).one()
    assert quote.request is not None
    assert len(quote.lines) == 4
