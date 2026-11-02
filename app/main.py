"""Applicazione FastAPI: middleware, rotte e pagina iniziale."""

from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import RedirectResponse, Response
from fastapi.staticfiles import StaticFiles
from starlette.middleware.sessions import SessionMiddleware

from app.config import settings
from app.deps import LoginRequired
from app.routes import agenda, auth, customers, overview
from app.templating import templates

# Script solo da qui e dai due file del CDN che usiamo (non da tutto jsdelivr),
# niente iframe da altri siti. 'unsafe-inline' sugli stili serve a Tailwind,
# che li genera nella pagina.
CONTENT_SECURITY_POLICY = (
    "default-src 'self'; "
    "script-src 'self' "
    "https://cdn.jsdelivr.net/npm/@tailwindcss/browser@4.1.11 "
    "https://cdn.jsdelivr.net/npm/htmx.org@2.0.4/dist/htmx.min.js; "
    "style-src 'self' 'unsafe-inline'; "
    "img-src 'self' data:; "
    "form-action 'self'; "
    "frame-ancestors 'none'; "
    "base-uri 'self'"
)

app = FastAPI(title="Bottega", docs_url=None, redoc_url=None, openapi_url=None)


@app.middleware("http")
async def security_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers["Content-Security-Policy"] = CONTENT_SECURITY_POLICY
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["Referrer-Policy"] = "same-origin"
    return response


# Il cookie di sessione è firmato con SECRET_KEY: se qualcuno lo modifica la firma
# non torna più e la sessione viene scartata. same_site="lax" fa sì che il browser
# non mandi il cookie con i form inviati da altri siti (protezione CSRF).
app.add_middleware(
    SessionMiddleware,
    secret_key=settings.secret_key.get_secret_value(),
    same_site="lax",
    https_only=settings.session_https_only,
    max_age=14 * 24 * 60 * 60,
)
app.mount("/static", StaticFiles(directory=Path(__file__).parent / "static"), name="static")

app.include_router(auth.router)
app.include_router(overview.router)
app.include_router(customers.router)
app.include_router(agenda.router)


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
