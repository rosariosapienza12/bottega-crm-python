import pytest

from app.insights import loyalty_label, loyalty_score
from app.money import format_euro, parse_euro
from app.phone import format_phone, normalize_phone, whatsapp_link


@pytest.mark.parametrize(
    "raw, expected",
    [
        ("333 123 4567", "+393331234567"),
        ("+39 333-123-4567", "+393331234567"),
        ("0041 79 123 45 67", "+41791234567"),
        ("(333) 123.4567", "+393331234567"),
    ],
)
def test_normalize_phone(raw, expected):
    assert normalize_phone(raw) == expected


@pytest.mark.parametrize("raw", ["", "abc", "12", "+39 333 abc 4567"])
def test_normalize_phone_rejects_garbage(raw):
    with pytest.raises(ValueError):
        normalize_phone(raw)


def test_format_phone():
    assert format_phone("+393331234567") == "+39 333 123 4567"
    assert format_phone("+41791234567") == "+41791234567"


def test_whatsapp_link_encodes_the_text():
    link = whatsapp_link("+393331234567", "Ciao Maria, a presto!")
    assert link == "https://wa.me/393331234567?text=Ciao%20Maria%2C%20a%20presto%21"


@pytest.mark.parametrize(
    "raw, cents",
    [("", 0), ("10", 1000), ("12,5", 1250), ("12.50", 1250), ("1.250,50", 125050), ("€ 3", 300)],
)
def test_parse_euro(raw, cents):
    assert parse_euro(raw) == cents


@pytest.mark.parametrize("raw", ["dieci", "-5", "1,234", "NaN", "Infinity"])
def test_parse_euro_rejects_bad_values(raw):
    with pytest.raises(ValueError):
        parse_euro(raw)


def test_format_euro():
    assert format_euro(0) == "0,00 €"
    assert format_euro(1250) == "12,50 €"
    assert format_euro(125050) == "1.250,50 €"


def test_loyalty_score():
    assert loyalty_score(0, 0) == 0
    assert loyalty_score(12, 600_00) == 100
    assert loyalty_score(24, 2000_00) == 100  # oltre il massimo non sale
    assert loyalty_score(6, 0) == 30
    assert loyalty_label(100) == "fedele"
    assert loyalty_label(40) == "abituale"
    assert loyalty_label(5) == "occasionale"
    assert loyalty_label(0) == "nuovo"
