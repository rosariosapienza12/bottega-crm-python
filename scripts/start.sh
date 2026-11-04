#!/bin/sh
# Avvio dell'app nel container Docker: prepara il database e accende il server.
# set -e: se un comando fallisce lo script si ferma, invece di avviare un'app a metà
set -e

# Crea o aggiorna le tabelle del database
alembic upgrade head

# Nella demo online carica l'attività di prova (lo script funziona solo su SQLite)
if [ "$DEMO_MODE" = "true" ]; then
    python -m scripts.crea_demo
fi

# --proxy-headers: dietro il proxy di Render l'IP vero del visitatore arriva in
# un header; senza, tutti avrebbero l'IP del proxy e il blocco dei tentativi di
# login fermerebbe tutti insieme. FORWARDED_ALLOW_IPS dice di quali proxy fidarsi.
# exec: uvicorn prende il posto dello script e riceve direttamente lo stop del server
exec uvicorn app.main:app \
    --host 0.0.0.0 \
    --port "${PORT:-8000}" \
    --proxy-headers \
    --forwarded-allow-ips "${FORWARDED_ALLOW_IPS:-127.0.0.1}"
