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
