"""Conti della cassa: incassi (visite + entrate a mano), spese, andamento per mese."""

from collections import defaultdict
from dataclasses import dataclass
from datetime import date

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import Customer, Movement, Visit

MONTH_NAMES = [
    "gennaio", "febbraio", "marzo", "aprile", "maggio", "giugno",
    "luglio", "agosto", "settembre", "ottobre", "novembre", "dicembre",
]


def month_start(day: date) -> date:
    return day.replace(day=1)


def add_months(day: date, months: int) -> date:
    """Primo giorno del mese spostato di `months` (anche negativo)."""
    index = day.year * 12 + day.month - 1 + months
    return date(index // 12, index % 12 + 1, 1)


@dataclass(frozen=True)
class MonthCash:
    start: date
    income_cents: int
    expense_cents: int

    @property
    def balance_cents(self) -> int:
        return self.income_cents - self.expense_cents

    @property
    def short_name(self) -> str:
        return MONTH_NAMES[self.start.month - 1][:3]

    @property
    def name(self) -> str:
        return f"{MONTH_NAMES[self.start.month - 1]} {self.start.year}"


def cash_between(db: Session, business_id: int, first: date, months: int) -> list[MonthCash]:
    """Entrate e uscite di `months` mesi a partire da `first` (primo del mese).

    Due query in tutto, poi si raggruppa per mese in Python: raggruppare per
    mese in SQL si scrive in modo diverso su SQLite e su PostgreSQL.
    """
    end = add_months(first, months)
    income: dict[date, int] = defaultdict(int)
    expense: dict[date, int] = defaultdict(int)

    visits = db.execute(
        select(Visit.visited_on, Visit.amount_cents)
        .join(Visit.customer)
        .where(Customer.business_id == business_id, Visit.visited_on >= first, Visit.visited_on < end)
    )
    for day, cents in visits:
        income[month_start(day)] += cents

    movements = db.execute(
        select(Movement.occurred_on, Movement.kind, Movement.amount_cents).where(
            Movement.business_id == business_id,
            Movement.occurred_on >= first,
            Movement.occurred_on < end,
        )
    )
    for day, kind, cents in movements:
        bucket = income if kind == "entrata" else expense
        bucket[month_start(day)] += cents

    starts = [add_months(first, i) for i in range(months)]
    return [MonthCash(start, income[start], expense[start]) for start in starts]


def month_cash(db: Session, business_id: int, start: date) -> MonthCash:
    return cash_between(db, business_id, start, 1)[0]


def last_months(db: Session, business_id: int, today: date, count: int = 6) -> list[MonthCash]:
    """Gli ultimi `count` mesi, dal più vecchio al mese in corso."""
    return cash_between(db, business_id, add_months(month_start(today), -(count - 1)), count)


def change_percent(now: int, before: int) -> int | None:
    """Variazione percentuale rispetto a prima. None se prima era zero."""
    if before == 0:
        return None
    return round((now - before) * 100 / before)


def expenses_by_category(db: Session, business_id: int, start: date) -> list[tuple[str, int]]:
    end = add_months(start, 1)
    rows = db.execute(
        select(Movement.category, func.sum(Movement.amount_cents))
        .where(
            Movement.business_id == business_id,
            Movement.kind == "uscita",
            Movement.occurred_on >= start,
            Movement.occurred_on < end,
        )
        .group_by(Movement.category)
        .order_by(func.sum(Movement.amount_cents).desc())
    ).all()
    return [(category, cents) for category, cents in rows]
