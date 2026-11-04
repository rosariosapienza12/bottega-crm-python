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

Il logout incrementa session_version dell'utente: un cookie copiato prima
del logout non vale più. Dopo 5 password sbagliate per la stessa email dallo
stesso IP il login si blocca per 15 minuti. La chiave è la coppia IP + email,
così uno sconosciuto non può bloccare il tuo account; dopo 20 tentativi da
uno stesso IP si blocca l'IP. Le registrazioni sono al massimo 10 l'ora per
IP. Tutto in memoria: con più server servirebbe Redis. Dietro un proxy
uvicorn va avviato con --proxy-headers, altrimenti tutti avrebbero l'IP del
proxy.

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

## Valore delle richieste: decide il preventivo
Una richiesta con preventivi vale quanto il più recente, e il campo valore
nella richiesta diventa di sola lettura. Così i totali della pipeline e della
Panoramica non vanno mai in disaccordo con i preventivi. "Prepara il
preventivo" su una richiesta che ne ha già uno apre quello: un doppio clic
non crea doppioni.

## Arrotondamenti dei soldi
Una sola funzione, round_half_up: 0,5 centesimi va su, come in negozio. Il
round() di Python arrotonda "al pari" (2,5 diventa 2): va bene per la
statistica, non per gli scontrini. Ogni riga del preventivo si arrotonda per
conto suo, così il subtotale è la somma esatta delle righe stampate.

## Errori dei form con htmx: 422
htmx di default non mostra le risposte 4xx. In base.html è configurato per
mostrare i 422 (dati del form sbagliati, con il messaggio) e ignorare gli
altri errori. Per questo "Fatto" con un importo assurdo risponde 400: htmx
lascia la riga com'è invece di toglierla.

## Limiti sui dati in ingresso
Importi fino a 10 milioni di euro, quantità fino a 9999, anni dal 1900 al
2200, ricerca fino a 5 parole. Il test di penetrazione ha mostrato che senza
limiti "1e9999" o "9999-12-31" mandavano il server in errore 500.

## Magazzino: il +1 lo fa il database
Una sola istruzione UPDATE. Leggere la quantità, sommare in Python e
riscrivere perderebbe un clic se ne arrivano due nello stesso istante
(race condition).

## Grafici disegnati dal server
Il grafico incassi/spese è un SVG generato da Jinja: nessuna libreria
JavaScript da caricare e aggiornare, e funziona anche senza JavaScript.

## Stile
Viola per struttura e azioni, verde per i soldi e le cose da guardare,
fondo bianco (prima era verde pino e senape su grigio-menta: cambiato a
novembre). Il tema di base è sempre quello chiaro, anche se il computer usa
il tema scuro: lo scuro si sceglie dal pulsante. Bricolage Grotesque per i titoli, Figtree per il testo,
con numeri incolonnati. Una sola cosa "forte" per pagina (il grafico, la
pipeline, lo scontrino del preventivo), il resto sobrio.

## Promemoria appuntamenti con un link wa.me
Il messaggio lo prepara Bottega, ma lo invia il titolare dal suo WhatsApp.
Le API di WhatsApp Business manderebbero tutto in automatico, ma servono un
account aziendale verificato e si paga ogni messaggio. Così invece è gratis e
il titolare può ritoccare il testo prima di inviarlo.

## Appuntamenti su due righe quando lo spazio è poco
Con una container query la tabella degli appuntamenti guarda la larghezza del
riquadro in cui si trova, non quella dello schermo. Così passa su due righe
(ora, cliente e servizio sopra, pulsanti sotto) sia su telefono sia nel
riquadro stretto "Oggi" della Panoramica su computer. Una media query avrebbe
sistemato solo il telefono.

## Demo online gratuita su Render, con Docker
Render ha un piano gratuito senza carta di credito per le app Python. Due
limiti: dopo 15 minuti senza visite il server si spegne (la prima pagina
dopo ci mette fino a un minuto) e il disco si azzera a ogni riavvio. Il
secondo limite lo usiamo a nostro favore: la versione online è una demo con
SQLite, che a ogni avvio ricrea l'attività di prova (`DEMO_MODE=true`).
Chi apre il link dal curriculum entra con un tocco e trova sempre dati puliti.
Alternative scartate: Railway (solo una prova a tempo), PythonAnywhere (nel
piano gratuito non supporta FastAPI). Per clienti veri servirà PostgreSQL
esterno: il codice è già pronto perché passa da SQLAlchemy.

Il Dockerfile fa girare l'app con un utente normale, non root. `render.yaml`
fa generare a Render la SECRET_KEY: non è scritta da nessuna parte.
`FORWARDED_ALLOW_IPS="*"` dice a uvicorn di fidarsi dell'IP scritto dal proxy:
va bene solo perché su Render il container si raggiunge esclusivamente
attraverso il loro proxy. Su un server esposto direttamente andrebbe messo
l'IP del proxy.

## La SECRET_KEY viene controllata all'avvio
Con la chiave d'esempio di `.env.example` (pubblica su GitHub) o una chiave
corta, chiunque potrebbe firmare un cookie finto ed entrare come un altro
utente. Per questo l'app si rifiuta di partire se la chiave ha meno di 32
caratteri o è quella d'esempio. Meglio un errore subito che un sito insicuro.
