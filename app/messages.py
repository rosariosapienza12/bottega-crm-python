"""Testi già pronti per i messaggi WhatsApp."""

from datetime import date, datetime


def comeback_text(first_name: str, business_name: str) -> str:
    return (
        f"Ciao {first_name}, è un po' che non ti vediamo da {business_name}! "
        "Se vuoi prenotare scrivici pure qui."
    )


def birthday_text(first_name: str, business_name: str) -> str:
    return f"Buon compleanno {first_name}! Tanti auguri da tutti noi di {business_name}."


def reminder_text(
    first_name: str,
    business_name: str,
    starts_at: datetime,
    service: str | None,
    today: date | None = None,
) -> str:
    # "today" si può passare dai test, così il risultato non dipende dal giorno in cui girano
    today = today or date.today()
    days = (starts_at.date() - today).days
    if days == 0:
        when = "oggi"
    elif days == 1:
        when = "domani"
    else:
        when = starts_at.strftime("il %d/%m")

    what = f" ({service})" if service else ""
    return (
        f"Ciao {first_name}, ti ricordiamo l'appuntamento da {business_name} "
        f"{when} alle {starts_at.strftime('%H:%M')}{what}. A presto!"
    )
