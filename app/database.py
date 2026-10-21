"""Connessione al database e sessioni SQLAlchemy."""

from sqlalchemy import create_engine, event
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from app.config import settings

# SQLite di base permette di usare una connessione solo dal thread che l'ha
# creata, ma FastAPI può gestire le richieste su thread diversi.
# Questa opzione serve solo a SQLite: PostgreSQL non ne ha bisogno.
connect_args = {}
if settings.database_url.startswith("sqlite"):
    connect_args = {"check_same_thread": False}

# L'engine è il "collegamento" al database: se ne crea uno solo per tutta l'app
engine = create_engine(settings.database_url, connect_args=connect_args)

if settings.database_url.startswith("sqlite"):

    @event.listens_for(engine, "connect")
    def enable_sqlite_foreign_keys(dbapi_connection, connection_record):
        """SQLite non controlla le chiavi esterne se non glielo chiediamo:
        questa funzione viene eseguita a ogni nuova connessione."""
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

# Fabbrica di sessioni: ogni richiesta HTTP avrà la sua sessione
SessionLocal = sessionmaker(bind=engine, autoflush=False)


class Base(DeclarativeBase):
    """Classe madre di tutti i modelli (le tabelle) del progetto."""


def get_db():
    """Apre una sessione per una richiesta e la chiude sempre alla fine.

    Si usa nelle rotte con Depends(get_db).
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
