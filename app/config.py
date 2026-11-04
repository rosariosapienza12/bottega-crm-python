"""Impostazioni lette dal file .env."""

import os
from pathlib import Path

from pydantic import SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_DIR = Path(__file__).resolve().parent.parent

MIN_SECRET_LENGTH = 32
# Il valore di esempio scritto in .env.example
PLACEHOLDER_SECRET = "cambiami-con-una-stringa-casuale"


class Settings(BaseSettings):
    # I test impostano BOTTEGA_ENV_FILE su un file che non esiste,
    # così non leggono mai il .env vero
    model_config = SettingsConfigDict(
        env_file=os.environ.get("BOTTEGA_ENV_FILE", BASE_DIR / ".env")
    )

    # Nessun default: se mancano nel .env l'app si ferma subito
    database_url: str
    # SecretStr: se finisce in un log o in un errore si vede "**********"
    secret_key: SecretStr
    # In produzione va messo a true: il cookie di login viaggia solo su HTTPS
    session_https_only: bool = False
    # Solo per la demo pubblica: pulsante "Prova la demo" e avviso sui dati di prova
    demo_mode: bool = False

    @field_validator("secret_key")
    @classmethod
    def reject_weak_secret(cls, key: SecretStr) -> SecretStr:
        # Con una chiave corta o copiata da .env.example (che è pubblico su GitHub)
        # chiunque potrebbe firmare un cookie finto ed entrare come un altro utente
        value = key.get_secret_value()
        if value == PLACEHOLDER_SECRET or len(value) < MIN_SECRET_LENGTH:
            raise ValueError(
                f"SECRET_KEY deve essere casuale e lunga almeno {MIN_SECRET_LENGTH} caratteri"
            )
        return key

    @field_validator("database_url")
    @classmethod
    def anchor_sqlite_path(cls, url: str) -> str:
        # Un percorso relativo dipenderebbe dalla cartella da cui si lancia
        # il comando (uvicorn, alembic...): lo leghiamo a quella del progetto
        prefix = "sqlite:///"
        if url.startswith(prefix) and url != prefix + ":memory:":
            path = Path(url.removeprefix(prefix))
            if not path.is_absolute():
                return prefix + (BASE_DIR / path).as_posix()
        return url


settings = Settings()
