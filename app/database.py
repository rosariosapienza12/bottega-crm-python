"""Engine e sessioni del database."""

from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker

from app.config import settings

is_sqlite = settings.database_url.startswith("sqlite")

# FastAPI può usare la connessione da un thread diverso da quello che l'ha
# aperta, e SQLite di default non lo permette
connect_args = {"check_same_thread": False} if is_sqlite else {}

engine = create_engine(settings.database_url, connect_args=connect_args)

if is_sqlite:

    @event.listens_for(engine, "connect")
    def enable_sqlite_foreign_keys(dbapi_connection, connection_record):
        # SQLite ignora le chiavi esterne se non le si attiva,
        # e va fatto a ogni nuova connessione
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()


SessionLocal = sessionmaker(bind=engine, autoflush=False)


def get_db():
    """Dipendenza FastAPI: una sessione per richiesta, chiusa sempre alla fine."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
