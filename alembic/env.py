"""Configurazione di Alembic: dice dove si trova il database e quali sono i modelli."""

from logging.config import fileConfig

from alembic import context

import app.models  # noqa: F401  (importa tutti i modelli, così Alembic li vede)
from app.config import settings
from app.database import Base, engine

config = context.config

# Configura i messaggi di log a partire da alembic.ini
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Lo "stato desiderato" del database: Alembic lo confronta con quello reale
# per generare le migrazioni (--autogenerate)
target_metadata = Base.metadata

# SQLite sa modificare poco le tabelle esistenti: la modalità "batch"
# ricrea la tabella e ricopia i dati quando serve
render_as_batch = settings.database_url.startswith("sqlite")


def run_migrations_offline() -> None:
    """Modalità offline: genera lo script SQL senza collegarsi al database."""
    context.configure(
        url=settings.database_url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        render_as_batch=render_as_batch,
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Modalità normale: si collega al database e applica le migrazioni.

    Usa lo stesso engine dell'app, quindi l'indirizzo arriva dal file .env.
    """
    with engine.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            render_as_batch=render_as_batch,
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
