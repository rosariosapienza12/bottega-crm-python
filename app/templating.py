"""Template Jinja2 condivisi da tutte le rotte, con i filtri per date e importi."""

from datetime import date
from decimal import Decimal
from pathlib import Path

from fastapi.templating import Jinja2Templates

from app.cash import MONTH_NAMES
from app.insights import loyalty_label
from app.messages import birthday_text, comeback_text
from app.money import format_euro
from app.phone import format_phone, whatsapp_link

DAY_NAMES = ["lunedì", "martedì", "mercoledì", "giovedì", "venerdì", "sabato", "domenica"]

templates = Jinja2Templates(directory=Path(__file__).parent / "templates")


def short_date(value: date) -> str:
    """date(2026, 11, 2) -> "2 nov" """
    return f"{value.day} {MONTH_NAMES[value.month - 1][:3]}"


def long_date(value: date) -> str:
    """date(2026, 11, 2) -> "lunedì 2 novembre 2026" """
    return f"{DAY_NAMES[value.weekday()]} {value.day} {MONTH_NAMES[value.month - 1]} {value.year}"


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


def amount_for_input(cents: int) -> str:
    """1250 -> "12,50", per riempire un campo del form (senza il simbolo €)."""
    return format_euro(cents).removesuffix(" €").replace(".", "")


def quantity(value: Decimal) -> str:
    """Decimal("1.50") -> "1,5", Decimal("2.00") -> "2" """
    text = f"{value:f}".rstrip("0").rstrip(".") if "." in f"{value:f}" else f"{value:f}"
    return text.replace(".", ",")


templates.env.filters["euro"] = format_euro
templates.env.filters["importo"] = amount_for_input
templates.env.filters["quantita"] = quantity
templates.env.filters["data"] = lambda value: value.strftime("%d/%m/%Y")
templates.env.filters["data_breve"] = short_date
templates.env.filters["data_lunga"] = long_date
templates.env.filters["giorni_fa"] = days_ago
templates.env.filters["tra_giorni"] = days_until
templates.env.filters["telefono"] = format_phone
templates.env.filters["fedelta"] = loyalty_label
templates.env.globals["whatsapp_link"] = whatsapp_link
templates.env.globals["comeback_text"] = comeback_text
templates.env.globals["birthday_text"] = birthday_text
