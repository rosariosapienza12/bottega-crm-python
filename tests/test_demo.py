"""Modalità demo: il pulsante "Prova la demo" esiste solo se DEMO_MODE è attivo."""

import pytest

from app.config import settings
from app.models import Business, User
from app.routes.auth import DEMO_EMAIL
from app.security import hash_password


@pytest.fixture
def demo_on(monkeypatch):
    monkeypatch.setattr(settings, "demo_mode", True)


def add_demo_account(db):
    business = Business(name="Salone Anna (prova)")
    db.add(User(email=DEMO_EMAIL, password_hash=hash_password("non-serve-nella-demo"), business=business))
    db.commit()


def test_without_demo_mode_there_is_no_demo_login(client, db):
    add_demo_account(db)

    # Sull'app vera nessuno deve poter entrare senza password
    assert client.post("/demo").status_code == 404
    assert "Prova la demo" not in client.get("/accedi").text


def test_demo_button_logs_into_the_demo_business(client, db, demo_on):
    add_demo_account(db)

    page = client.get("/")
    assert "Prova la demo" in page.text
    assert "i dati sono di prova" in page.text

    response = client.post("/demo", follow_redirects=False)
    assert response.status_code == 303
    assert response.headers["location"] == "/panoramica"
    assert "Salone Anna (prova)" in client.get("/panoramica").text


def test_demo_without_the_demo_account_goes_back_to_login(client, demo_on):
    response = client.post("/demo", follow_redirects=False)

    assert response.headers["location"] == "/accedi"
