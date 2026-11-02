"""Applicazione FastAPI e rotte."""

from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

# Percorso assoluto, così uvicorn trova i template da qualsiasi cartella
TEMPLATES_DIR = Path(__file__).parent / "templates"

app = FastAPI(title="Bottega")
templates = Jinja2Templates(directory=TEMPLATES_DIR)


@app.get("/", response_class=HTMLResponse)
def home(request: Request):
    return templates.TemplateResponse(request, "index.html", {"app_name": "Bottega"})
