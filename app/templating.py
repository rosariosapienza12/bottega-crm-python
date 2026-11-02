"""Template Jinja2 condivisi da tutte le rotte, con i filtri per date e importi."""

from datetime import date
from pathlib import Path

from fastapi.templating import Jinja2Templates

from app.insights import loyalty_label
from app.messages import birthday_text, comeback_text
from app.money import format_euro
from app.phone import format_phone, whatsapp_link

MONTHS = ["gen", "feb", "mar", "apr", "mag", "giu", "lug", "ago", "set", "ott", "nov", "dic"]

templates = Jinja2Templates(directory=Path(__file__).parent / "templates")


def short_date(value: date) -> str:
    """date(2026, 11, 2) -> "2 nov" """
    return f"{value.day} {MONTHS[value.month - 1]}"


def days_ago(value: date) -> str:
    days = (date.today() - value).days
    if days == 0:
        return "oggi"
    if days == 1:
        return "ieri"
    return f"{days} giorni fa"


def days_until(value: date) -> str:
    days = (value - date.today()).days
    if days == 0:
        return "oggi"
    if days == 1:
        return "domani"
    return f"tra {days} giorni"


templates.env.filters["euro"] = format_euro
templates.env.filters["data"] = lambda value: value.strftime("%d/%m/%Y")
templates.env.filters["data_breve"] = short_date
templates.env.filters["giorni_fa"] = days_ago
templates.env.filters["tra_giorni"] = days_until
templates.env.filters["telefono"] = format_phone
templates.env.filters["fedelta"] = loyalty_label
templates.env.globals["whatsapp_link"] = whatsapp_link
templates.env.globals["comeback_text"] = comeback_text
templates.env.globals["birthday_text"] = birthday_text
