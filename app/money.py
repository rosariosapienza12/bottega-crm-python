"""Importi in euro, salvati come centesimi interi."""

import re
from decimal import Decimal, InvalidOperation

# Oltre è di sicuro un errore di battitura (o qualcuno che prova a rompere l'app):
# senza tetto "1e9999" faceva fallire quantize() con un errore 500
MAX_EURO = Decimal(10_000_000)


def parse_euro(raw: str) -> int:
    """ "12,50" -> 1250. Campo vuoto = 0. Solleva ValueError se non è un importo."""
    text = raw.strip().replace("€", "").replace(" ", "")
    if not text:
        return 0
    # All'italiana il punto separa le migliaia: "1.250,50" e anche "1.250" senza
    # virgola, che altrimenti diventerebbe 1,25 €. "12.50" resta un decimale.
    if "," in text or re.fullmatch(r"\d{1,3}(\.\d{3})+", text):
        text = text.replace(".", "").replace(",", ".")
    try:
        value = Decimal(text)
    except InvalidOperation:
        raise ValueError(f"importo non valido: {raw!r}") from None
    # L'ordine conta: il tetto va controllato prima di quantize()
    if (
        not value.is_finite()
        or value < 0
        or value > MAX_EURO
        or value != value.quantize(Decimal("0.01"))
    ):
        raise ValueError(f"importo non valido: {raw!r}")
    return int(value * 100)


def format_euro(cents: int) -> str:
    """1250 -> "12,50 €", 125000 -> "1.250,00 €"."""
    text = f"{cents / 100:,.2f}"
    return text.replace(",", "_").replace(".", ",").replace("_", ".") + " €"
