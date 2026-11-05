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

Nel pomeriggio: l'app diventa usabile.

- Registrazione e login, password con Argon2, sessione in un cookie firmato.
- Schede clienti con ricerca dal vivo e ordinamento, visite con importo,
  note modificabili sul posto, pulsante WhatsApp.
- Agenda settimanale: un appuntamento passato si segna come "fatto" con
  l'incasso e diventa una visita.
- Panoramica con appuntamenti di oggi, clienti da ricontattare e compleanni.
- Punteggio fedeltà.
- Header di sicurezza e test che provano a leggere i clienti di un'altra
  attività. 68 test in tutto.

Cosa ho imparato:
- Come funziona htmx: il server risponde con un pezzo di HTML, non con JSON.
- Perché i soldi non si salvano con i float.
- Cos'è un attacco CSRF e cosa fa `SameSite=Lax`.
- Cos'è un IDOR: cambiare un id nell'indirizzo per vedere dati di altri.

In serata: le funzioni del gestionale completo.

- Pipeline delle richieste con trascinamento tra colonne (e menu a tendina
  per telefono e tastiera).
- Preventivatore: righe con costo, sconto, IVA, margine, versione da stampare.
- Cassa con grafico degli ultimi sei mesi e spese per categoria.
- Magazzino con pulsanti - e +, scorta minima, avvisi in Panoramica.
- Nuova grafica: barra laterale, tema chiaro e scuro, font Bricolage
  Grotesque e Figtree.
- Sicurezza: limite ai login e alle registrazioni, logout che invalida i
  cookie copiati, controllo dell'origine dei POST, SRI sugli script del CDN.
- Test di penetrazione con curl e due revisioni automatiche (codice e
  sicurezza). Hanno trovato errori veri: "1.250" letto come 1,25 euro, un
  importo enorme che mandava il server in errore, date tipo 9999 che
  rompevano la cassa, errori dei form che htmx non mostrava. Corretti, con un
  test per ognuno. 134 test in tutto.
- Controllato tutto da telefono: niente esce dallo schermo o si sovrappone.

Cosa ho imparato:
- Cos'è un N+1 e come si risolve con joinedload / selectinload.
- Perché l'arrotondamento "al pari" di Python non va bene per i soldi.
- Cos'è una race condition, e perché il +1 del magazzino lo fa il database.
- Che min-width: 0 sugli elementi di una griglia evita che la pagina sbordi.

## 4 novembre 2026

- Colori nuovi: viola e bianco. Bastava cambiare le variabili in cima a
  style.css (e print.css per il preventivo da stampare).
- Nei dati di prova le richieste avevano l'occasione nel titolo ("per la
  comunione della figlia"): ora c'è solo il trattamento.
- Promemoria WhatsApp sugli appuntamenti futuri, in agenda, Panoramica e
  scheda cliente. Messaggio con oggi / domani / data, ora e trattamento.
- Test: i casi del testo, il link solo sugli appuntamenti futuri e un nome
  "cattivo" con dentro uno <script>. 140 test in tutto.

Cosa ho imparato:
- Passare la data di oggi come parametro rende il test sempre uguale
  (deterministico), qualunque giorno lo lanci.
- Contro l'XSS ci sono due difese: la codifica del link (quote) e
  l'escaping automatico di Jinja.
- Il browser tiene in memoria i file CSS: dopo un cambio serve Ctrl+F5.

Più tardi:

- Tema bianco e viola di base anche con il computer in tema scuro; il giallo
  senape è diventato verde.
- Controllo da telefono di tutte le pagine. Nell'agenda nome e servizio si
  sovrapponevano: ora ogni appuntamento va su due righe quando lo spazio è poco.
- README aggiornato, con due screenshot.

Cosa ho imparato:
- Cos'è una container query e la differenza con una media query.
- X-Frame-Options impedisce di mostrare le pagine dentro un iframe: è una
  difesa contro il clickjacking.

Sera:

- Revisione di sicurezza prima di mettere l'app online. Corretti tre punti:
  l'app non parte con una SECRET_KEY debole o d'esempio, lo script della demo
  funziona solo su SQLite, e gli id nei form accettano solo cifre 0-9.
- Modalità demo: pulsante "Prova la demo" e striscia che avvisa che i dati
  sono finti. Senza DEMO_MODE la rotta /demo risponde 404.
- Dockerfile, script di avvio e render.yaml per la demo gratuita su Render.
  Immagine provata: parte, carica i dati di prova e gira senza root.
- 151 test in tutto.

Cosa ho imparato:
- "²".isdigit() è vero ma int("²") va in errore: per i numeri meglio una
  regex con [0-9].
- Un test che prima di una correzione fallisce e dopo passa dimostra che la
  correzione serve davvero.
- Dietro un proxy l'app vede l'IP del proxy, non quello del visitatore:
  serve --proxy-headers, e bisogna dire di quali proxy fidarsi.
- Nel Dockerfile si copia prima requirements.txt e poi il codice, così Docker
  riusa le librerie già installate quando cambia solo il codice.

Ancora:

- Tailwind e htmx ora sono file del sito (app/static/vendor) e non arrivano
  più da un CDN. Nel mio ambiente di prova il CDN era bloccato e le pagine
  sembravano rotte da telefono: con le librerie vere tutte le pagine stanno
  nello schermo e le tabelle scorrono dentro il loro riquadro.
- Da telefono il menu va a capo su due righe: prima "Preventivi", "Cassa" e
  "Magazzino" erano nascosti in una striscia da scorrere.

Cosa ho imparato:
- Prima di correggere un "bug" bisogna essere sicuri di misurare la cosa
  giusta: il problema era nell'ambiente di prova, non nell'app.
- Copiare una libreria nel progetto ("vendoring") toglie una dipendenza
  esterna; in cambio va aggiornata a mano.

Notte:

- Niente Render: la demo andrà su Vercel con il database PostgreSQL su Neon,
  come Lumora. Il CRM ora parla con PostgreSQL (psycopg 3) e le migrazioni
  le fa l'app all'avvio.
- La demo è diventata personale: ogni visitatore riceve il suo Salone di
  prova, che si cancella dopo 24 ore. Provato su PostgreSQL vero: due
  visitatori non si vedono a vicenda e la pulizia cancella tutto.
- Tolto render.yaml. 159 test, passano anche con Python 3.12 (quello di
  Vercel).

Cosa ho imparato:
- Un database che "resta" cambia il modo di fare una demo: con SQLite che si
  azzera bastava un account condiviso, con PostgreSQL serve un'attività per
  visitatore.
- Un advisory lock di PostgreSQL è un lucchetto con un numero come nome:
  chi arriva secondo aspetta.
- Il dominio .invalid è riservato: nessuna email ci può arrivare.

Dopo la messa online:

- Il CRM era lento a cambiare sezione: codice negli USA e database in Europa.
  Ho contato le query di ogni pagina (la Panoramica ne fa 12) e spostato il
  codice a Francoforte con vercel.json.
- Su un PC grande il contenuto occupava solo una parte dello schermo: tolto il
  limite di larghezza.
- Nella pagina iniziale c'era un'anteprima con appuntamenti finti: ora c'è
  l'elenco delle funzioni principali.
- Nel menu, al posto dell'indirizzo lunghissimo dell'account demo, c'è
  "Account di prova".

Cosa ho imparato:
- La latenza (il tempo di andata e ritorno) si moltiplica per il numero di
  query: 12 query × 90 ms = più di un secondo.
- Prima di ottimizzare bisogna misurare: Tailwind nel browser sembrava un
  sospetto, ma non era lui il problema.

## 5 novembre 2026

- Pagina "Non trovato" con la grafica dell'app, al posto del JSON tecnico;
  gli id strani o enormi nell'indirizzo danno 404 invece di 500 (provato
  anche su PostgreSQL).
- Richieste: le 5 colonne stanno tutte nello schermo da 1280 px in su.
- README con il link alla demo online e immagini nuove, anche da telefono.
- 165 test.

Cosa ho imparato:
- FastAPI permette di intercettare gli errori (exception handler) e
  rispondere con una pagina invece del JSON.
- Un errore 500 per un input dell'utente è quasi sempre un 404 o un 400
  mancato: il server non deve "rompersi" per un indirizzo scritto male.
