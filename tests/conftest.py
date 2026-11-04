import os

# Prima di importare l'app: configurazione finta, il .env vero non viene letto
os.environ["BOTTEGA_ENV_FILE"] = "file-che-non-esiste.env"
os.environ["DATABASE_URL"] = "sqlite://"
os.environ["SECRET_KEY"] = "chiave-finta-solo-per-i-test-lunga-abbastanza"

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from sqlalchemy import create_engine  # noqa: E402
from sqlalchemy.orm import Session, sessionmaker  # noqa: E402
from sqlalchemy.pool import StaticPool  # noqa: E402

from app.database import get_db  # noqa: E402
from app.main import app  # noqa: E402
from app.models import Base  # noqa: E402
from app.ratelimit import ip_limiter, login_limiter, signup_limiter  # noqa: E402

PASSWORD = "una-password-lunga"


@pytest.fixture
def engine():
    """Database SQLite in memoria, vuoto per ogni test.

    StaticPool: una sola connessione condivisa, altrimenti ogni connessione
    vedrebbe un database in memoria diverso (e vuoto).
    """
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    Base.metadata.create_all(engine)
    yield engine
    engine.dispose()


@pytest.fixture
def db(engine):
    with Session(engine) as session:
        yield session


@pytest.fixture
def client(engine):
    """Client HTTP che usa il database del test al posto di quello vero."""
    TestSession = sessionmaker(bind=engine, autoflush=False)

    def test_db():
        session = TestSession()
        try:
            yield session
        finally:
            session.close()

    app.dependency_overrides[get_db] = test_db
    with TestClient(app) as client:
        yield client
    app.dependency_overrides.clear()


@pytest.fixture(autouse=True)
def reset_limiters():
    # I limitatori vivono in memoria per tutto il processo: ogni test riparte da zero
    for limiter in (login_limiter, ip_limiter, signup_limiter):
        limiter.reset_all()
    yield


def register(client, business_name="Salone Anna", email="anna@example.com"):
    return client.post(
        "/registrati",
        data={"business_name": business_name, "email": email, "password": PASSWORD},
    )


@pytest.fixture
def logged_in(client):
    """Client già registrato e loggato come "Salone Anna"."""
    register(client)
    return client
