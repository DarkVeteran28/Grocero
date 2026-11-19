from decimal import Decimal

from app.services.units import line_total_paise, per_unit_paise, unit_suffix
from app.utils.money import format_money, to_paise


def test_per_unit_normalisation():
    assert per_unit_paise(4000, Decimal("0.5")) == 8000
    assert per_unit_paise(5600, Decimal("1")) == 5600
    assert per_unit_paise(4800, Decimal("6")) == 800
    assert unit_suffix("g") == "kg"
    assert unit_suffix("ml") == "L"
    assert unit_suffix("piece") == "pc"


def test_line_total_uses_decimal_quantity():
    assert line_total_paise(10000, Decimal("1.5")) == 15000
    assert line_total_paise(10000, Decimal("2")) == 20000


def test_money_format_and_parse():
    assert format_money(123456789) == "₹1,234,567.89"
    assert format_money(0) == "₹0.00"
    assert format_money(-50) == "-₹0.50"
    assert to_paise("1,234.50") == 123450
    assert to_paise("40", allow_zero=True) == 4000
    try:
        to_paise("0")
        raised = False
    except ValueError:
        raised = True
    assert raised
    try:
        to_paise("1.234")
        raised = False
    except ValueError:
        raised = True
    assert raised
