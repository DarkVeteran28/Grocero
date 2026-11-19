"""Pack-size normalisation."""

from decimal import Decimal, ROUND_HALF_UP


def as_decimal(value) -> Decimal:
    if isinstance(value, Decimal):
        return value
    return Decimal(str(value))


def per_unit_paise(price_paise: int, base_unit_qty) -> int:
    qty = as_decimal(base_unit_qty)
    if qty <= 0:
        raise ValueError("Base quantity must be greater than 0.")
    per_unit = (Decimal(int(price_paise)) / qty).quantize(Decimal("1"), rounding=ROUND_HALF_UP)
    return int(per_unit)


def line_total_paise(unit_price_paise: int, quantity) -> int:
    total = (Decimal(int(unit_price_paise)) * as_decimal(quantity)).quantize(
        Decimal("1"), rounding=ROUND_HALF_UP
    )
    return int(total)


def unit_suffix(unit: str) -> str:
    key = (unit or "").lower()
    if key in {"kg", "g"}:
        return "kg"
    if key in {"l", "ml"}:
        return "L"
    return "pc"
