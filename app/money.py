"""Importi in euro, salvati come centesimi interi."""

from decimal import Decimal, InvalidOperation


def parse_euro(raw: str) -> int:
    """ "12,50" -> 1250. Campo vuoto = 0. Solleva ValueError se non è un importo."""
    text = raw.strip().replace("€", "").replace(" ", "")
    if not text:
        return 0
    # "1.250,50" all'italiana: il punto separa le migliaia
    if "," in text:
        text = text.replace(".", "").replace(",", ".")
    try:
        value = Decimal(text)
    except InvalidOperation:
        raise ValueError(f"importo non valido: {raw!r}") from None
    if not value.is_finite() or value < 0 or value != value.quantize(Decimal("0.01")):
        raise ValueError(f"importo non valido: {raw!r}")
    return int(value * 100)


def format_euro(cents: int) -> str:
    """1250 -> "12,50 €", 125000 -> "1.250,00 €"."""
    text = f"{cents / 100:,.2f}"
    return text.replace(",", "_").replace(".", ",").replace("_", ".") + " €"
