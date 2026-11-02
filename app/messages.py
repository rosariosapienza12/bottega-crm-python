"""Testi già pronti per i messaggi WhatsApp."""


def comeback_text(first_name: str, business_name: str) -> str:
    return (
        f"Ciao {first_name}, è un po' che non ti vediamo da {business_name}! "
        "Se vuoi prenotare scrivici pure qui."
    )


def birthday_text(first_name: str, business_name: str) -> str:
    return f"Buon compleanno {first_name}! Tanti auguri da tutti noi di {business_name}."
