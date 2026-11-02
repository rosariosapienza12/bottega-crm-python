"""Numeri di telefono e link a WhatsApp."""

import re
from urllib.parse import quote


def normalize_phone(raw: str) -> str:
    """Porta il numero in formato internazionale: "333 123 4567" -> "+393331234567".

    Senza prefisso si assume un numero italiano. Solleva ValueError se non è un numero.
    """
    number = re.sub(r"[\s\-./()]", "", raw)
    if number.startswith("00"):
        number = "+" + number[2:]
    elif not number.startswith("+"):
        number = "+39" + number
    if not re.fullmatch(r"\+\d{8,15}", number):
        raise ValueError(f"numero di telefono non valido: {raw!r}")
    return number


def format_phone(phone: str) -> str:
    """ "+393331234567" -> "+39 333 123 4567". Gli altri numeri restano come sono."""
    if phone.startswith("+39") and len(phone) == 13:
        return f"+39 {phone[3:6]} {phone[6:9]} {phone[9:]}"
    return phone


def whatsapp_link(phone: str, text: str) -> str:
    # wa.me vuole solo le cifre, senza "+"
    return f"https://wa.me/{phone.lstrip('+')}?text={quote(text)}"
