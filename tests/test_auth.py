from sqlalchemy import select

from app.models import User
from tests.conftest import PASSWORD, register


def test_register_logs_in_and_hashes_the_password(client, db):
    response = register(client)

    assert response.status_code == 200  # dopo il redirect alla Panoramica
    assert "Panoramica" in response.text
    user = db.scalars(select(User)).one()
    assert user.business.name == "Salone Anna"
    assert user.password_hash != PASSWORD
    assert user.password_hash.startswith("$argon2")


def test_register_rejects_short_password(client):
    response = client.post(
        "/registrati",
        data={"business_name": "Salone", "email": "a@example.com", "password": "corta"},
    )

    assert response.status_code == 400
    assert "almeno 8 caratteri" in response.text


def test_register_rejects_email_already_used(client):
    register(client)
    client.post("/esci")

    response = register(client, business_name="Altro salone")

    assert response.status_code == 400
    assert "Esiste già un account" in response.text


def test_login_with_wrong_password_fails(client):
    register(client)
    client.post("/esci")

    response = client.post(
        "/accedi", data={"email": "anna@example.com", "password": "sbagliata"}
    )

    assert response.status_code == 400
    assert "Email o password sbagliate" in response.text


def test_login_and_logout(client):
    register(client)
    client.post("/esci")

    response = client.post(
        "/accedi", data={"email": "ANNA@example.com ", "password": PASSWORD}
    )
    assert "Panoramica" in response.text

    client.post("/esci")
    response = client.get("/panoramica", follow_redirects=False)
    assert response.status_code == 303
    assert response.headers["location"] == "/accedi"


def test_private_pages_need_login(client):
    for path in ["/panoramica", "/clienti", "/clienti/nuovo"]:
        response = client.get(path, follow_redirects=False)
        assert response.status_code == 303, path
        assert response.headers["location"] == "/accedi"


def test_htmx_request_without_login_gets_hx_redirect(client):
    response = client.get("/clienti", headers={"HX-Request": "true"})

    assert response.headers["HX-Redirect"] == "/accedi"


def test_session_cookie_is_httponly_and_samesite(client):
    response = register(client)

    cookie = response.history[0].headers["set-cookie"].lower()
    assert "httponly" in cookie
    assert "samesite=lax" in cookie
