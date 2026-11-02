"""Crea un'attività di prova con clienti, visite e appuntamenti, per provare l'app.

Uso (dalla cartella del progetto, dopo `alembic upgrade head`):

    python -m scripts.crea_demo

Poi accedi con l'email e la password qui sotto. Sono credenziali solo per
provare l'app sul proprio PC: non usarle su un'app messa online.
"""

from datetime import date, datetime, timedelta

from sqlalchemy import select

from app.database import SessionLocal
from app.models import Appointment, Business, Customer, User, Visit
from app.security import hash_password

DEMO_EMAIL = "demo@bottega.test"
DEMO_PASSWORD = "prova-bottega-2026"

# (nome, cognome, telefono, compleanno tra N giorni o None, note,
#  visite come (giorni fa, euro, cosa))
CUSTOMERS = [
    ("Maria", "Rossi", "+393331234567", 3, "Allergica all'ammoniaca. Preferisce il sabato mattina.",
     [(95, 45, "Colore e piega"), (140, 38, "Taglio"), (190, 45, "Colore e piega")]),
    ("Luca", "Bianchi", "+393471112222", None, None,
     [(4, 20, "Taglio uomo"), (35, 20, "Taglio uomo"), (66, 20, "Taglio uomo"), (97, 25, "Taglio e barba")]),
    ("Giulia", "Esposito", "+393289998877", None, None,
     [(12, 65, "Meches"), (50, 35, "Piega")]),
    ("Francesca", "Romano", "+393405556677", 10, "Porta sempre la figlia, Sofia.",
     [(200, 25, "Piega")]),
    ("Paolo", "Greco", "+393381234000", None, None, []),
    ("Chiara", "Conti", "+393479876543", None, "Capelli molto sottili, niente piastra.",
     [(7, 55, "Taglio e colore"), (28, 30, "Piega"), (56, 55, "Taglio e colore"), (84, 30, "Piega")]),
]

# (nome del cliente, tra quante ore, servizio)
APPOINTMENTS = [
    ("Chiara", -2, "Piega"),
    ("Luca", 2, "Taglio uomo"),
    ("Maria", 26, "Colore"),
    ("Giulia", 50, "Taglio"),
]


def birthday_in(days: int, born: int = 1990) -> date:
    target = date.today() + timedelta(days=days)
    return date(born, target.month, min(target.day, 28))


def main() -> None:
    db = SessionLocal()
    if db.scalar(select(User).where(User.email == DEMO_EMAIL)):
        print(f"L'attività di prova esiste già. Accedi con {DEMO_EMAIL}.")
        return

    business = Business(name="Salone Anna (prova)")
    db.add(User(email=DEMO_EMAIL, password_hash=hash_password(DEMO_PASSWORD), business=business))

    by_name = {}
    for first, last, phone, birthday_days, notes, visits in CUSTOMERS:
        customer = Customer(
            business=business,
            first_name=first,
            last_name=last,
            phone=phone,
            birth_date=birthday_in(birthday_days) if birthday_days is not None else None,
            notes=notes,
        )
        for days_ago, euro, what in visits:
            customer.visits.append(
                Visit(
                    visited_on=date.today() - timedelta(days=days_ago),
                    amount_cents=euro * 100,
                    note=what,
                )
            )
        db.add(customer)
        by_name[first] = customer

    now = datetime.now().replace(minute=0, second=0, microsecond=0)
    for first, hours, service in APPOINTMENTS:
        db.add(
            Appointment(
                customer=by_name[first], starts_at=now + timedelta(hours=hours), service=service
            )
        )

    db.commit()
    print(f"Fatto. Accedi con {DEMO_EMAIL} (la password è in scripts/crea_demo.py).")


if __name__ == "__main__":
    main()
