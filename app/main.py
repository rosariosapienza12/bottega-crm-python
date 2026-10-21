"""Punto di partenza dell'applicazione Bottega."""

from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

# Cartella dei template, calcolata a partire da questo file:
# così funziona da qualunque cartella venga avviato il server.
TEMPLATES_DIR = Path(__file__).parent / "templates"

app = FastAPI(title="Bottega")
templates = Jinja2Templates(directory=TEMPLATES_DIR)


@app.get("/", response_class=HTMLResponse)
def home(request: Request):
    """Pagina iniziale: risponde quando il browser apre l'indirizzo "/"."""
    return templates.TemplateResponse(request, "index.html", {"app_name": "Bottega"})
