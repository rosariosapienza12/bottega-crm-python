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

## Date e orari
Le visite hanno solo la data (`date`), gli appuntamenti data e ora senza
fuso (`datetime` "naive") nell'ora locale dell'attività: un appuntamento
alle 15 deve restare alle 15, anche se il server sta in un altro paese.
Clienti dormienti e compleanni usano solo date, quindi il fuso non conta.
Restano in UTC solo `created_at` e `updated_at`, che per ora non servono
a nessun calcolo. Il giorno in cui l'app avrà attività in fusi diversi,
il fuso andrà salvato nell'attività.

## Importi in centesimi interi
Con i float `0.10 + 0.20` fa `0.30000000000000004`. Gli importi si salvano
come centesimi (`int`) e si convertono solo per mostrarli ("12,50 €").
Il parsing accetta il formato italiano ("1.250,50").

## Login con cookie di sessione firmato
`SessionMiddleware` di Starlette salva l'id dell'utente in un cookie firmato
con `SECRET_KEY`: se qualcuno lo modifica, la firma non torna. Il cookie è
`HttpOnly` (JavaScript non lo legge) e `SameSite=Lax`, che protegge dai form
inviati da altri siti (CSRF). In produzione va messo `SESSION_HTTPS_ONLY=true`.
Alternativa scartata: JWT. Per un sito con pagine generate dal server non
serve, e un cookie di sessione è più semplice da spiegare e da gestire.

Limiti che conosco: il cookie resta valido fino alla scadenza (14 giorni)
anche dopo il logout, se qualcuno l'ha copiato; non c'è un limite ai
tentativi di login. Da sistemare prima di andare online.

## Ogni query filtra per attività
Ogni cliente, visita e appuntamento si cerca sempre insieme al `business_id`
dell'utente loggato (`get_customer`, `get_appointment`). Se l'id non è
dell'attività giusta la risposta è 404, non 403: non diciamo nemmeno che
quel cliente esiste. Ci sono test che provano ad accedere ai dati di
un'altra attività.

## HTMX invece di un framework JavaScript
Le parti interattive (ricerca, visite, note, agenda) chiedono al server un
pezzo di HTML e htmx lo sostituisce nella pagina. I template che iniziano
con `_` sono questi pezzi. Tutta la logica resta in Python ed è testabile
con pytest. Quando un'azione deve aggiornare un'altra parte della pagina
(un appuntamento "fatto" diventa una visita) il server manda l'evento
`HX-Trigger: visitsChanged`.

## Header di sicurezza
Content-Security-Policy: script solo dal sito e dai due file del CDN che
usiamo, niente iframe. In più `X-Content-Type-Options: nosniff` e
`Referrer-Policy`. La documentazione automatica di FastAPI (`/docs`) è
spenta: non serve a chi usa l'app e mostrerebbe tutte le rotte.
Tailwind dal CDN va bene solo in sviluppo: in produzione si compila.

## Punteggio fedeltà
Da 0 a 100: 60 punti per la frequenza (una visita al mese = pieno) e 40 per
la spesa (600 € l'anno = pieno), sugli ultimi 12 mesi. Conta di più la
frequenza perché un cliente che torna spesso vale più di uno che ha speso
tanto una volta. Le soglie sono pensate per un salone e vanno tarate.
L'ordinamento per fedeltà si fa in Python e non in SQL: per qualche
centinaio di clienti è veloce e il codice resta leggibile.

## Test su un database SQLite in memoria
Ogni test parte da un database vuoto (`StaticPool`, una sola connessione)
e una configurazione finta: non tocca `bottega.db` né il `.env`.
