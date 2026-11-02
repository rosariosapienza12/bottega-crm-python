"""Date che arrivano dai form o dall'indirizzo: solo anni sensati.

Senza un limite "9999-12-31" passa la validazione, ma poi "il mese dopo" o
"la settimana dopo" vanno oltre l'anno 9999 e Python solleva un errore.
"""

from datetime import date, datetime, time

MIN_YEAR = 1900
MAX_YEAR = 2200


def parse_day(raw: str) -> date:
    """ "2026-11-02" -> date. Solleva ValueError se non è valida o l'anno è assurdo."""
    day = date.fromisoformat(raw.strip())
    if not MIN_YEAR <= day.year <= MAX_YEAR:
        raise ValueError(f"anno fuori dai limiti: {raw!r}")
    return day


def parse_start(day: str, hour: str) -> datetime:
    """Data e ora dei campi del form -> datetime. Solleva ValueError se non validi."""
    return datetime.combine(parse_day(day), time.fromisoformat(hour.strip()))
