# Decisioni tecniche

## FastAPI + Jinja2 + HTMX invece di un frontend React
Le pagine vengono generate dal server. Per un gestionale semplice basta e
avanza, e c'è un solo linguaggio (Python) da imparare bene invece di due.
HTMX aggiunge le parti interattive senza scrivere molto JavaScript.

## SQLite in sviluppo, PostgreSQL in produzione
SQLite è un file e non va installato niente. In produzione serve un database
vero, che regga più utenti insieme. SQLAlchemy permette di cambiare database
cambiando solo `DATABASE_URL`.

## Alembic per le modifiche al database
`create_all()` crea le tabelle ma non sa modificarle. Con le migrazioni ogni
modifica è un file nel repository, e lo stesso database si ricrea uguale
ovunque. Con SQLite si usa la modalità batch, perché SQLite non supporta
quasi nessun `ALTER TABLE`.

## Configurazione nel file `.env`, senza valori predefiniti
`DATABASE_URL` e `SECRET_KEY` devono stare nel `.env`. Se mancano l'app non
parte: meglio un errore subito che una chiave finta finita in produzione.
`SECRET_KEY` è un `SecretStr` per non stamparla per sbaglio.

## Percorso di SQLite legato alla cartella del progetto
`sqlite:///bottega.db` sarebbe relativo alla cartella da cui si lancia il
comando. Lanciando `alembic` da un'altra cartella si creava un database
nuovo e vuoto. Ora il percorso viene sempre calcolato dalla cartella del
progetto.

## Un'attività per utente, separazione per `business_id`
Ogni utente e ogni cliente ha un `business_id`. Tutte le query dovranno
filtrare per l'attività dell'utente loggato. Alternativa scartata: un
database per attività, troppo complicato da gestire per un progetto così.

## Cancellazione a cascata gestita da SQLAlchemy
Cancellando un `Business` si cancellano i suoi utenti e clienti
(`cascade="all, delete-orphan"`). Per ora la cascata è solo lato
SQLAlchemy, quindi vale quando si cancella passando dall'app. Se servirà,
si aggiungerà anche `ondelete="CASCADE"` nel database con una migrazione.

## Password con Argon2 (pwdlib)
Argon2 è l'algoritmo consigliato oggi per le password: è lento apposta e
usa molta memoria, così un attacco a forza bruta costa molto.

## Date e fusi orari: rimandato
SQLite salva `CURRENT_TIMESTAMP` in UTC senza fuso, PostgreSQL usa il fuso
del server. Va sistemato prima di costruire "clienti dormienti" e
compleanni, con dei test sulle date. Farlo adesso, senza una funzione che
usa le date, sarebbe andare a intuito.

## Test su un database SQLite in memoria
Ogni test parte da un database vuoto e non tocca `bottega.db` né il `.env`.
