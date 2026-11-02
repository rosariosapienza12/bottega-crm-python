# Diario

## 21 ottobre 2026

Ho iniziato il progetto.

- Preparato `.gitignore` e `.env.example`, così i segreti restano fuori da GitHub.
- Creata un'app FastAPI minima con una pagina iniziale fatta con Jinja2.
- Le impostazioni ora si leggono dal file `.env` con pydantic-settings.
- Collegato il database con SQLAlchemy e creati i primi modelli:
  `Business`, `User` e `Customer`.
- Prima migrazione con Alembic.

Cosa ho imparato:
- A cosa serve un ambiente virtuale e perché `.env` non va su Git.
- Cos'è una chiave esterna, e che SQLite non le controlla finché non si
  attiva `PRAGMA foreign_keys`.
- Perché una migrazione è meglio di `create_all()`: tiene traccia delle
  modifiche al database nel tempo.

## 2 novembre 2026

Revisione e pulizia di quello che c'era.

- Tolti i commenti che ripetevano il codice, lasciati quelli che spiegano
  una scelta.
- Il percorso del database SQLite ora parte sempre dalla cartella del
  progetto: prima dipendeva da dove lanciavo il comando.
- `SECRET_KEY` è un `SecretStr`, così non compare mai in chiaro nei log.
- Cancellando un'attività si cancellano anche i suoi utenti e clienti.
- `Base` spostata in `app/models/base.py`: i modelli non dipendono più
  dalla connessione al database.
- Primi test con pytest (pagina iniziale e modelli), su un database in memoria.
- README riscritto e aggiornato, nuova grafica della pagina iniziale.
- Controllato che `.env` non sia mai finito su GitHub.

Cosa ho imparato:
- La differenza tra percorso relativo e assoluto, e perché conta per SQLite.
- Cos'è una fixture di pytest.
- Cosa fa `cascade="all, delete-orphan"` in una relationship.
