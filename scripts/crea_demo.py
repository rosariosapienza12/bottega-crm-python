"""Crea un'attività di prova con clienti, visite e appuntamenti, per provare l'app sul PC.

Uso (dalla cartella del progetto, dopo `alembic upgrade head`):

    python -m scripts.crea_demo

Poi accedi con l'email e la password qui sotto. Sono credenziali pubbliche,
scritte qui su GitHub: per questo lo script funziona solo con SQLite (il PC di
sviluppo) e si rifiuta di partire su PostgreSQL, cioè su un database con
clienti veri. La demo online non usa questo script: ogni visitatore riceve
un'attività tutta sua (vedi app/demo.py).
"""

from sqlalchemy import select

from app.config import settings
from app.database import SessionLocal
from app.demo import DEMO_BUSINESS_NAME, fill_demo_business
from app.models import Business, User
from app.security import hash_password

DEMO_EMAIL = "demo@bottega.test"
DEMO_PASSWORD = "prova-bottega-2026"


def check_local_database(database_url: str) -> None:
    """Ferma lo script se il database non è SQLite: lì potrebbero esserci clienti veri."""
    if not database_url.startswith("sqlite"):
        raise SystemExit(
            "crea_demo funziona solo con SQLite: non creo un account con password "
            "pubblica su un database di produzione."
        )


def main() -> None:
    check_local_database(settings.database_url)
    db = SessionLocal()
    user = db.scalar(select(User).where(User.email == DEMO_EMAIL))
    if user is None:
        business = Business(name=DEMO_BUSINESS_NAME)
        db.add(User(email=DEMO_EMAIL, password_hash=hash_password(DEMO_PASSWORD), business=business))
        db.flush()
    else:
        business = user.business
    fill_demo_business(db, business)
    db.commit()
    print(f"Fatto. Accedi con {DEMO_EMAIL} (la password è in scripts/crea_demo.py).")


if __name__ == "__main__":
    main()
