"""Format and parse money. Storage is integer paise; arithmetic uses Decimal."""

from decimal import Decimal, InvalidOperation, ROUND_HALF_UP

from app.config import CURRENCY_SYMBOL, DECIMAL_PLACES, THOUSANDS_SEPARATOR


def money_settings(symbol=None, thousands_sep=None, decimals=None):
    cfg_symbol = CURRENCY_SYMBOL
    cfg_sep = THOUSANDS_SEPARATOR
    cfg_decimals = DECIMAL_PLACES
    try:
        from flask import current_app, has_app_context

        if has_app_context():
            cfg_symbol = current_app.config.get("CURRENCY_SYMBOL", cfg_symbol)
            cfg_sep = current_app.config.get("THOUSANDS_SEPARATOR", cfg_sep)
            cfg_decimals = current_app.config.get("DECIMAL_PLACES", cfg_decimals)
    except RuntimeError:
        pass
    return (
        cfg_symbol if symbol is None else symbol,
        cfg_sep if thousands_sep is None else thousands_sep,
        cfg_decimals if decimals is None else decimals,
    )


def format_money(paise, symbol=None, thousands_sep=None, decimals=None) -> str:
    symbol, thousands_sep, decimals = money_settings(symbol, thousands_sep, decimals)
    decimals = int(decimals)
    negative = int(paise) < 0
    amount = (Decimal(abs(int(paise))) / Decimal(100)).quantize(
        Decimal("1").scaleb(-decimals), rounding=ROUND_HALF_UP
    )
    text = f"{amount:.{decimals}f}"
    whole, frac = text.split(".")
    groups = []
    while whole:
        groups.append(whole[-3:])
        whole = whole[:-3]
    grouped = thousands_sep.join(reversed(groups)) if groups else "0"
    sign = "-" if negative else ""
    return f"{sign}{symbol}{grouped}.{frac}"


def chart_amount(paise) -> float:
    """Major currency units for Chart.js. The API computes this; the browser only plots it."""
    return float((Decimal(int(paise)) / Decimal(100)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))


def to_paise(value, *, allow_zero=False) -> int:
    if isinstance(value, bool) or value is None:
        raise ValueError("Enter a valid amount.")
    if isinstance(value, str):
        text = value.strip().replace(",", "")
        if text.startswith(CURRENCY_SYMBOL):
            text = text[len(CURRENCY_SYMBOL) :].strip()
        if text.startswith("Rs"):
            text = text[2:].strip()
        if not text:
            raise ValueError("Enter a valid amount.")
    else:
        text = str(value)
    try:
        amount = Decimal(text)
    except InvalidOperation as exc:
        raise ValueError("Enter a valid amount.") from exc
    if not amount.is_finite():
        raise ValueError("Enter a valid amount.")
    exponent = amount.as_tuple().exponent
    if isinstance(exponent, int) and exponent < -2:
        raise ValueError("Use at most 2 decimal places.")
    if amount < 0 or (amount == 0 and not allow_zero):
        raise ValueError("Amount must be greater than 0." if not allow_zero else "Amount cannot be negative.")
    return int((amount * 100).to_integral_value(rounding=ROUND_HALF_UP))
