"""Migrazioni del database fatte dall'app stessa, quando si avvia.

Su Vercel non c'è un momento "prima di partire" in cui lanciare `alembic upgrade
head` a mano: con MIGRATE_ON_STARTUP=true ci pensa l'app. Se il database è già
aggiornato, Alembic controlla la versione e non fa niente.
"""

from pathlib import Path

from alembic import command
from alembic.config import Config
from sqlalchemy import text

from app import database

ALEMBIC_INI = Path(__file__).resolve().parent.parent / "alembic.ini"

# Un numero qualsiasi, uguale per tutte le copie dell'app: è il nome del "lucchetto"
MIGRATION_LOCK = 7_210_402


def upgrade_database() -> None:
    config = Config(str(ALEMBIC_INI))
    if database.is_sqlite:
        command.upgrade(config, "head")
        return
    # Con PostgreSQL due copie dell'app possono partire insieme: il lucchetto
    # (advisory lock) fa aspettare la seconda finché la prima ha finito
    with database.engine.connect() as connection:
        connection.execute(text("SELECT pg_advisory_lock(:id)"), {"id": MIGRATION_LOCK})
        try:
            command.upgrade(config, "head")
        finally:
            connection.execute(text("SELECT pg_advisory_unlock(:id)"), {"id": MIGRATION_LOCK})
