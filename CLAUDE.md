# Progetto: Bottega — CRM per piccole attività

## Contesto
- Sono uno studente universitario e principiante nella programmazione.
- Questo progetto andrà nel mio curriculum e su GitHub: deve essere fatto bene
  e io devo saperlo spiegare in un colloquio.
- Parlami sempre in italiano. Uso Windows con PowerShell.

## Visione del prodotto
- Utente target: titolari di piccole attività (parrucchieri, estetisti,
  palestre, negozi, B&B) che oggi gestiscono i clienti su carta o WhatsApp.
- Problema: perdono i clienti abituali perché non si ricordano di ricontattarli,
  e non hanno una visione chiara di chi sono i clienti migliori.
- Funzioni base: schede clienti, appuntamenti, storico visite e acquisti, note.
- Funzioni distintive:
  - "Clienti dormienti": elenco di chi non torna da troppo tempo.
  - Punteggio fedeltà calcolato da frequenza e spesa.
  - Pulsante per inviare un messaggio WhatsApp precompilato (link wa.me).
  - Promemoria compleanni.
  - Più attività separate: ogni titolare vede solo i propri clienti.
  - Riassunto con IA della storia di un cliente.

## Stack (non cambiarlo senza propormelo)
- Python + FastAPI, SQLAlchemy, SQLite in sviluppo e PostgreSQL in produzione.
- Frontend con template Jinja2 + HTMX + Tailwind.
- Test con pytest. Deploy con Docker.

## Modalità di lavoro: devo imparare
- Prima di ogni funzionalità proponimi un piano e aspetta il mio ok.
- Lavora a piccoli passi. Dopo ogni passo spiegami:
  1) cosa hai fatto, 2) perché in questo modo, 3) quale alternativa hai scartato.
- Quando introduci un concetto nuovo, spiegamelo con un esempio semplice prima di usarlo.
- Ogni tanto lascia a me una parte da scrivere: dammi le istruzioni,
  poi correggi il mio codice spiegandomi gli errori.
- Alla fine di ogni funzionalità fammi 2-3 domande da colloquio.

## Documentazione del percorso
- Tieni aggiornato DIARIO.md: per ogni sessione, cosa abbiamo fatto e cosa ho imparato.
- Tieni aggiornato DECISIONI.md: ogni scelta tecnica importante con il motivo.
- Il README.md deve essere sempre aggiornato e in inglese (è per i recruiter).

## Qualità
- Ogni funzionalità deve avere almeno un test.
- Dopo ogni passo che funziona, proponimi un commit Git con un messaggio chiaro.
- Codice semplice e leggibile, commenti in italiano, nomi in inglese.

## Sicurezza
- Password e chiavi solo nel file .env, che deve essere nel .gitignore.
- Le password degli utenti vanno sempre salvate con hash, mai in chiaro.
- Chiedimi conferma prima di cancellare file o dati, installare pacchetti
  o modificare più di 3 file insieme.
