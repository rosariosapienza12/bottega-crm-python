"""Configurazione di Alembic: usa lo stesso database e gli stessi modelli dell'app."""

from logging.config import fileConfig

from alembic import context

from app.config import settings
from app.database import engine
from app.models import Base

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata

# SQLite non sa fare quasi nessun ALTER TABLE: in modalità batch Alembic
# ricrea la tabella e ricopia i dati
render_as_batch = settings.database_url.startswith("sqlite")


def run_migrations_offline() -> None:
    """Genera lo script SQL senza collegarsi al database."""
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
    """Si collega al database e applica le migrazioni."""
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
