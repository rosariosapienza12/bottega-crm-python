"""Applicazione FastAPI: middleware, rotte e pagina iniziale."""

from pathlib import Path
from urllib.parse import urlsplit

from fastapi import FastAPI, Request
from fastapi.responses import PlainTextResponse, RedirectResponse, Response
from fastapi.staticfiles import StaticFiles
from starlette.middleware.sessions import SessionMiddleware

from app.config import settings
from app.deps import LoginRequired
from app.routes import agenda, auth, cash, customers, inventory, overview, pipeline, quotes
from app.templating import templates

# Script solo dal nostro sito (anche Tailwind e htmx sono in app/static/vendor),
# font da Google Fonts, niente iframe da altri siti. 'unsafe-inline' sugli stili
# serve a Tailwind, che li genera nella pagina. Gli script non hanno 'unsafe-inline':
# un <script> iniettato da un attaccante non parte.
CONTENT_SECURITY_POLICY = (
    "default-src 'self'; "
    "script-src 'self'; "
    "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; "
    "font-src https://fonts.gstatic.com; "
    "img-src 'self' data:; "
    "connect-src 'self'; "
    "form-action 'self'; "
    "frame-ancestors 'none'; "
    "base-uri 'self'; "
    "object-src 'none'"
)

UNSAFE_METHODS = {"POST", "PUT", "PATCH", "DELETE"}

if settings.migrate_on_startup:
    # Prima di accettare richieste il database deve avere tutte le tabelle
    from app.migrate import upgrade_database

    upgrade_database()

app = FastAPI(title="Bottega", docs_url=None, redoc_url=None, openapi_url=None)


@app.middleware("http")
async def security_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers["Content-Security-Policy"] = CONTENT_SECURITY_POLICY
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "same-origin"
    response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
    if settings.session_https_only:
        response.headers["Strict-Transport-Security"] = "max-age=31536000"
    if not request.url.path.startswith("/static/"):
        # Pagine con dati dei clienti: il browser non le tiene in cache,
        # così dopo il logout il tasto "indietro" non le mostra
        response.headers["Cache-Control"] = "no-store"
    return response


@app.middleware("http")
async def same_origin_only(request: Request, call_next):
    """Seconda difesa contro il CSRF, oltre al cookie SameSite.

    I browser mettono Origin (o almeno Referer) nelle richieste che modificano dati:
    se viene da un altro sito la blocchiamo. Senza nessuno dei due (curl, test)
    la lasciamo passare: senza il cookie di sessione non può comunque fare nulla.
    """
    if request.method in UNSAFE_METHODS:
        source = request.headers.get("origin") or request.headers.get("referer")
        if source and urlsplit(source).netloc != request.headers.get("host"):
            return PlainTextResponse("Richiesta da un altro sito bloccata.", status_code=403)
    return await call_next(request)


# Il cookie di sessione è firmato con SECRET_KEY: se qualcuno lo modifica la firma
# non torna più e la sessione viene scartata. same_site="lax" fa sì che il browser
# non mandi il cookie con i form inviati da altri siti (protezione CSRF).
app.add_middleware(
    SessionMiddleware,
    secret_key=settings.secret_key.get_secret_value(),
    session_cookie="bottega_session",
    same_site="lax",
    https_only=settings.session_https_only,
    max_age=14 * 24 * 60 * 60,
)
app.mount("/static", StaticFiles(directory=Path(__file__).parent / "static"), name="static")

for module in (auth, overview, customers, agenda, pipeline, quotes, cash, inventory):
    app.include_router(module.router)


@app.exception_handler(LoginRequired)
def redirect_to_login(request: Request, exc: LoginRequired):
    if request.headers.get("HX-Request") == "true":
        # Con htmx un redirect normale finirebbe dentro un pezzo di pagina
        return Response(headers={"HX-Redirect": "/accedi"})
    return RedirectResponse("/accedi", status_code=303)


@app.get("/")
def home(request: Request):
    if request.session.get("user_id"):
        return RedirectResponse("/panoramica", status_code=303)
    return templates.TemplateResponse(request, "index.html", {})
