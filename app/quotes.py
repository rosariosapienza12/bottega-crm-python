"""Calcoli del preventivatore: subtotale, sconto, IVA, totale e margine."""

from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal, InvalidOperation
from typing import Iterable, Protocol


class LineLike(Protocol):
    quantity: Decimal
    unit_price_cents: int
    unit_cost_cents: int


@dataclass(frozen=True)
class QuoteTotals:
    subtotal_cents: int
    discount_cents: int
    taxable_cents: int
    vat_cents: int
    total_cents: int
    cost_cents: int
    # Margine sull'imponibile (senza IVA, che non è nostra)
    margin_cents: int
    margin_percent: int | None


def round_half_up(value: Decimal | int) -> int:
    # Arrotondamento commerciale: 0,5 va su, non "al pari" come fa round() di Python
    return int(Decimal(value).quantize(Decimal(1), rounding=ROUND_HALF_UP))


def line_total_cents(quantity: Decimal, unit_cents: int) -> int:
    return round_half_up(Decimal(quantity) * unit_cents)


def compute_totals(
    lines: Iterable[LineLike], discount_percent: int, vat_percent: int
) -> QuoteTotals:
    lines = list(lines)
    # Ogni riga si arrotonda per conto suo: così il subtotale è proprio
    # la somma degli importi che il cliente legge riga per riga
    subtotal = sum(line_total_cents(line.quantity, line.unit_price_cents) for line in lines)
    cost = sum(line_total_cents(line.quantity, line.unit_cost_cents) for line in lines)
    discount = round_half_up(Decimal(subtotal) * discount_percent / 100)
    taxable = subtotal - discount
    vat = round_half_up(Decimal(taxable) * vat_percent / 100)
    margin = taxable - cost
    return QuoteTotals(
        subtotal_cents=subtotal,
        discount_cents=discount,
        taxable_cents=taxable,
        vat_cents=vat,
        total_cents=taxable + vat,
        cost_cents=cost,
        margin_cents=margin,
        margin_percent=round_half_up(Decimal(margin) * 100 / taxable) if taxable else None,
    )


def parse_quantity(raw: str) -> Decimal:
    """ "1,5" -> Decimal("1.5"). Deve essere > 0, al massimo 2 decimali e 9999."""
    text = raw.strip().replace(",", ".") or "1"
    try:
        value = Decimal(text)
    except InvalidOperation:
        raise ValueError(f"quantità non valida: {raw!r}") from None
    if (
        not value.is_finite()
        or value <= 0
        or value > 9999
        or value != value.quantize(Decimal("0.01"))
    ):
        raise ValueError(f"quantità non valida: {raw!r}")
    return value


def parse_percent(raw: str, maximum: int = 100) -> int:
    text = raw.strip().replace("%", "") or "0"
    if not text.isdigit() or int(text) > maximum:
        raise ValueError(f"percentuale non valida: {raw!r}")
    return int(text)
