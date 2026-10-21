"""Impostazioni dell'applicazione, lette dal file .env."""

from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

# Cartella principale del progetto (quella che contiene .env)
BASE_DIR = Path(__file__).parent.parent


class Settings(BaseSettings):
    # Ogni attributo corrisponde a una variabile del file .env
    # (DATABASE_URL -> database_url: maiuscole e minuscole non contano).
    database_url: str = "sqlite:///./bottega.db"
    # Nessun valore predefinito: se manca nel .env l'app non parte.
    # Meglio un errore subito che una chiave segreta finta in produzione.
    secret_key: str

    model_config = SettingsConfigDict(env_file=BASE_DIR / ".env")


# Un'unica istanza condivisa da tutta l'applicazione
settings = Settings()
