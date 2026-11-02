"""Calcoli per la Panoramica: clienti dormienti e compleanni."""

from datetime import date, timedelta

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import Customer, Visit

# Dopo quanti giorni senza visite un cliente è "da ricontattare"
DORMANT_AFTER_DAYS = 60
BIRTHDAY_WINDOW_DAYS = 14


def dormant_customers(db: Session, business_id: int, today: date):
    """Clienti con almeno una visita, ma nessuna negli ultimi DORMANT_AFTER_DAYS giorni.

    Restituisce coppie (cliente, data dell'ultima visita), dal più "dimenticato".
    """
    last_visit = func.max(Visit.visited_on)
    limit = today - timedelta(days=DORMANT_AFTER_DAYS)
    query = (
        select(Customer, last_visit)
        .join(Customer.visits)
        .where(Customer.business_id == business_id)
        .group_by(Customer.id)
        .having(last_visit < limit)
        .order_by(last_visit)
    )
    return db.execute(query).all()


def next_birthday(birth_date: date, today: date) -> date:
    for year in (today.year, today.year + 1):
        try:
            birthday = birth_date.replace(year=year)
        except ValueError:
            # Nato il 29 febbraio: negli anni non bisestili lo festeggiamo il 1° marzo
            birthday = date(year, 3, 1)
        if birthday >= today:
            return birthday
    raise AssertionError("non dovrebbe mai succedere")


def upcoming_birthdays(db: Session, business_id: int, today: date):
    """Coppie (cliente, data del compleanno) nei prossimi BIRTHDAY_WINDOW_DAYS giorni."""
    customers = db.scalars(
        select(Customer).where(
            Customer.business_id == business_id, Customer.birth_date.is_not(None)
        )
    )
    result = []
    for customer in customers:
        birthday = next_birthday(customer.birth_date, today)
        if (birthday - today).days <= BIRTHDAY_WINDOW_DAYS:
            result.append((customer, birthday))
    return sorted(result, key=lambda pair: pair[1])


# Una visita al mese e 600 € l'anno valgono il punteggio pieno.
# Sono soglie pensate per un salone: andranno tarate con i dati veri.
FULL_SCORE_VISITS_PER_YEAR = 12
FULL_SCORE_CENTS_PER_YEAR = 600_00


def loyalty_score(visits_last_year: int, cents_last_year: int) -> int:
    """Punteggio fedeltà da 0 a 100: conta di più la frequenza (60) della spesa (40)."""
    frequency = min(visits_last_year / FULL_SCORE_VISITS_PER_YEAR, 1)
    spending = min(cents_last_year / FULL_SCORE_CENTS_PER_YEAR, 1)
    return round(60 * frequency + 40 * spending)


def loyalty_label(score: int) -> str:
    if score >= 70:
        return "fedele"
    if score >= 35:
        return "abituale"
    if score > 0:
        return "occasionale"
    return "nuovo"


def customer_loyalty(customer: Customer, today: date) -> int:
    since = today - timedelta(days=365)
    recent = [visit for visit in customer.visits if visit.visited_on >= since]
    return loyalty_score(len(recent), sum(visit.amount_cents for visit in recent))


def month_totals(db: Session, business_id: int, today: date) -> tuple[int, int]:
    """Numero di visite e incasso (in centesimi) del mese in corso."""
    query = (
        select(func.count(Visit.id), func.coalesce(func.sum(Visit.amount_cents), 0))
        .join(Visit.customer)
        .where(
            Customer.business_id == business_id,
            Visit.visited_on >= today.replace(day=1),
        )
    )
    count, cents = db.execute(query).one()
    return count, cents
