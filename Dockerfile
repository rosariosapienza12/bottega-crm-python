# Immagine per mettere Bottega online (Render, o qualsiasi server con Docker).
# Versione "slim": Python senza gli strumenti che non servono, immagine più piccola
FROM python:3.13-slim

# Niente file .pyc e log subito visibili (non trattenuti in un buffer)
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# Prima solo requirements.txt: se cambia il codice ma non le librerie,
# Docker riusa questo passaggio già pronto e la build è più veloce
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# L'app non gira come root: se qualcuno trovasse una falla, avrebbe meno permessi
RUN useradd --create-home bottega && chown -R bottega /app
USER bottega

CMD ["sh", "scripts/start.sh"]
