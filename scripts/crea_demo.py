"""Crea un'attività di prova con clienti, visite e appuntamenti, per provare l'app.

Uso (dalla cartella del progetto, dopo `alembic upgrade head`):

    python -m scripts.crea_demo

Poi accedi con l'email e la password qui sotto. Sono credenziali pubbliche,
scritte qui su GitHub: per questo lo script funziona solo con SQLite (il PC di
sviluppo o la demo online) e si rifiuta di partire su PostgreSQL, cioè su un
database con clienti veri.
"""

from datetime import date, datetime, timedelta
from decimal import Decimal

from sqlalchemy import select

from app.cash import add_months
from app.config import settings
from app.database import SessionLocal
from app.models import (
    Appointment,
    Business,
    Customer,
    Movement,
    Product,
    Quote,
    QuoteLine,
    Request,
    User,
    Visit,
)
from app.quotes import compute_totals
from app.routes.auth import DEMO_EMAIL
from app.security import hash_password

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


# (titolo, cliente o None, nome se non è cliente, valore in euro, fase)
REQUESTS = [
    ("Trucco e acconciatura sposa", None, "Sara (Instagram)", 280, "nuova"),
    ("Colore", "Francesca", None, 60, "contattata"),
    ("Pacchetto 5 pieghe", "Giulia", None, 120, "preventivo"),
    ("Trattamento cheratina", None, "Elena (passaparola)", 150, "nuova"),
    ("Taglio e barba", "Luca", None, 45, "confermata"),
    ("Extension", None, "Marta", 400, "persa"),
]

# (descrizione, quantità, prezzo €, costo €) per il preventivo della sposa
QUOTE_LINES = [
    ("Prova trucco e acconciatura", "1", 80, 10),
    ("Trucco sposa il giorno del matrimonio", "1", 120, 15),
    ("Acconciatura sposa", "1", 100, 8),
    ("Uscita a domicilio (ore)", "1.5", 30, 12),
]

# (nome, quantità, scorta minima, costo €)
PRODUCTS = [
    ("Tinta castano 5.0", 2, 3, 7.5),
    ("Tinta biondo 8.0", 6, 3, 7.5),
    ("Ossigeno 20 vol", 0, 2, 4.2),
    ("Shampoo professionale 1 l", 4, 2, 9.9),
    ("Lacca forte", 9, 4, 5.4),
]


def birthday_in(days: int, born: int = 1990) -> date:
    target = date.today() + timedelta(days=days)
    return date(born, target.month, min(target.day, 28))


def check_local_database(database_url: str) -> None:
    """Ferma lo script se il database non è SQLite: lì potrebbero esserci clienti veri."""
    if not database_url.startswith("sqlite"):
        raise SystemExit(
            "crea_demo funziona solo con SQLite: non creo un account con password "
            "pubblica su un database di produzione."
        )


def main() -> None:
    check_local_database(settings.database_url)
    db = SessionLocal()
    user = db.scalar(select(User).where(User.email == DEMO_EMAIL))
    if user is None:
        business = Business(name="Salone Anna (prova)")
        db.add(User(email=DEMO_EMAIL, password_hash=hash_password(DEMO_PASSWORD), business=business))
    else:
        business = user.business

    # Ogni parte si aggiunge solo se manca: lo script si può rilanciare
    if not business.customers:
        add_customers_and_appointments(db, business)
    if not business.requests:
        add_requests_and_quote(db, business)
    if not business.movements:
        add_movements(db, business)
    if not business.products:
        for name, quantity, minimum, cost in PRODUCTS:
            business.products.append(
                Product(
                    name=name, quantity=quantity,
                    min_quantity=minimum, unit_cost_cents=round(cost * 100),
                )
            )

    db.commit()
    print(f"Fatto. Accedi con {DEMO_EMAIL} (la password è in scripts/crea_demo.py).")


def add_requests_and_quote(db, business) -> None:
    customers = {c.first_name: c for c in business.customers}
    for position, (title, first, contact, euro, stage) in enumerate(REQUESTS, start=1):
        business.requests.append(
            Request(
                title=title, customer=customers.get(first),
                contact_name=contact, value_cents=euro * 100, stage=stage, position=position,
            )
        )
    db.flush()
    bride = next(r for r in business.requests if r.title.startswith("Trucco e acconciatura"))
    quote = Quote(request=bride, title=bride.title, discount_percent=5)
    for description, quantity, price, cost in QUOTE_LINES:
        quote.lines.append(
            QuoteLine(
                description=description, quantity=Decimal(quantity),
                unit_price_cents=price * 100, unit_cost_cents=cost * 100,
            )
        )
    business.quotes.append(quote)
    db.flush()  # i valori predefiniti (IVA 22%) arrivano col salvataggio
    bride.value_cents = compute_totals(quote.lines, quote.discount_percent, quote.vat_percent).total_cents


def add_movements(db, business) -> None:
    this_month = date.today().replace(day=1)
    for months_back in range(6):
        start = add_months(this_month, -months_back)
        expenses = [(1, 650, "Affitto"), (8, 180 + 15 * months_back, "Prodotti"), (15, 95, "Bollette")]
        for day, euro, category in expenses:
            occurred = start.replace(day=day)
            if occurred <= date.today():
                business.movements.append(
                    Movement(
                        kind="uscita", occurred_on=occurred,
                        amount_cents=euro * 100, category=category,
                    )
                )
        if months_back % 2 == 0:
            business.movements.append(
                Movement(
                    kind="entrata", occurred_on=start,
                    amount_cents=240_00, category="Vendita prodotti",
                )
            )


def add_customers_and_appointments(db, business) -> None:
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
    db.flush()


if __name__ == "__main__":
    main()
