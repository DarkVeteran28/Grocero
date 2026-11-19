"""Request parsing. Low-level money parsing lives in utils.money."""

import re
from datetime import datetime
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP

from flask import request

from app.utils.errors import ValidationError
from app.utils.money import to_paise

UNITS = {"kg", "g", "L", "ml", "piece"}
STORE_TYPES = {"supermarket", "local kirana", "online", "wholesale"}
MONTH_RE = re.compile(r"^\d{4}-\d{2}$")


def fail(fields):
    if fields:
        raise ValidationError("Validation failed", {"fields": fields})


def json_body():
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        raise ValidationError("Expected a JSON object.", {"fields": {"body": "Send a JSON object."}})
    return data


def parse_quantity(value, *, allow_zero=False) -> Decimal:
    if isinstance(value, bool) or value is None:
        raise ValueError("Enter a quantity greater than 0.")
    text = str(value).strip()
    try:
        amount = Decimal(text)
    except InvalidOperation as exc:
        raise ValueError("Enter a quantity greater than 0.") from exc
    if not amount.is_finite():
        raise ValueError("Enter a quantity greater than 0.")
    exponent = amount.as_tuple().exponent
    if isinstance(exponent, int) and exponent < -2:
        raise ValueError("Use at most 2 decimal places.")
    amount = amount.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    if amount == 0 and allow_zero:
        return amount
    if amount <= 0:
        raise ValueError("Quantity must be greater than 0.")
    if amount > Decimal("999"):
        raise ValueError("Quantity cannot exceed 999.")
    return amount


def parse_date(value):
    if not isinstance(value, str):
        raise ValueError("Use a date in YYYY-MM-DD format.")
    try:
        return datetime.strptime(value, "%Y-%m-%d").date()
    except ValueError as exc:
        raise ValueError("Use a date in YYYY-MM-DD format.") from exc


def parse_month(value) -> str:
    if not isinstance(value, str) or not MONTH_RE.match(value):
        raise ValueError("Use a month in YYYY-MM format.")
    year, month = int(value[:4]), int(value[5:])
    if year < 2000 or year > 2100 or not 1 <= month <= 12:
        raise ValueError("Use a month in YYYY-MM format.")
    return value


def parse_bool(value):
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)) and value in (0, 1):
        return bool(value)
    if isinstance(value, str):
        text = value.strip().lower()
        if text in {"true", "yes", "1", "y"}:
            return True
        if text in {"false", "no", "0", "n"}:
            return False
    raise ValueError("Use true or false.")


def parse_int(value, field):
    if isinstance(value, bool) or value is None:
        raise ValueError(f"Enter a valid {field}.")
    try:
        return int(str(value))
    except (TypeError, ValueError) as exc:
        raise ValueError(f"Enter a valid {field}.") from exc


def _text(data, key, errors, *, min_len=1, max_len=120):
    value = data.get(key)
    if not isinstance(value, str) or not value.strip():
        errors[key] = "This field is required."
        return None
    value = value.strip()
    if len(value) > max_len or len(value) < min_len:
        errors[key] = f"Use between {min_len} and {max_len} characters."
        return None
    return value


def validate_store(data):
    errors = {}
    name = _text(data, "name", errors, max_len=120)
    area = _text(data, "area", errors, max_len=80)
    store_type = data.get("type")
    if store_type not in STORE_TYPES:
        errors["type"] = "Choose a valid store type."
    distance = None
    try:
        distance = Decimal(str(data.get("distance_km")).strip())
        if not distance.is_finite() or distance < 0 or distance > Decimal("1000"):
            raise ValueError
        exponent = distance.as_tuple().exponent
        if isinstance(exponent, int) and exponent < -2:
            raise ValueError
        distance = distance.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    except (InvalidOperation, ValueError, AttributeError):
        errors["distance_km"] = "Enter a distance from 0 to 1000."
    delivery = None
    try:
        delivery = to_paise(data.get("delivery_fee"), allow_zero=True)
    except ValueError as exc:
        errors["delivery_fee"] = str(exc)
    free = data.get("free_delivery_above")
    free_paise = None
    if free not in (None, ""):
        try:
            free_paise = to_paise(free)
        except ValueError as exc:
            errors["free_delivery_above"] = str(exc)
    rating = None
    try:
        rating = Decimal(str(data.get("rating")).strip())
        if not rating.is_finite() or rating < 0 or rating > 5:
            raise ValueError
        rating = rating.quantize(Decimal("0.1"), rounding=ROUND_HALF_UP)
    except (InvalidOperation, ValueError, AttributeError):
        errors["rating"] = "Enter a rating from 0 to 5."
    fail(errors)
    return {
        "name": name,
        "type": store_type,
        "area": area,
        "distance_km": distance,
        "delivery_fee": delivery,
        "free_delivery_above": free_paise,
        "rating": rating,
    }


def validate_product(data, *, category_ids):
    errors = {}
    name = _text(data, "name", errors, max_len=160)
    brand = _text(data, "brand", errors, max_len=80)
    pack_size = _text(data, "pack_size", errors, max_len=32)
    unit = data.get("unit")
    if isinstance(unit, str):
        unit = unit.strip()
    if unit == "l":
        unit = "L"
    if unit not in UNITS:
        errors["unit"] = "Unit must be kg, g, L, ml, or piece."
    try:
        category_id = parse_int(data.get("category_id"), "category")
        if category_id not in category_ids:
            errors["category_id"] = "Choose a category that exists."
    except ValueError as exc:
        errors["category_id"] = str(exc)
        category_id = None
    base_qty = None
    try:
        base_qty = Decimal(str(data.get("base_unit_qty")).strip())
        if not base_qty.is_finite() or base_qty <= 0 or base_qty > Decimal("100000"):
            raise ValueError
        base_qty = base_qty.quantize(Decimal("0.0001"), rounding=ROUND_HALF_UP)
    except (InvalidOperation, ValueError, AttributeError):
        errors["base_unit_qty"] = "Enter a base quantity greater than 0."
    fail(errors)
    return {
        "name": name,
        "brand": brand,
        "category_id": category_id,
        "pack_size": pack_size,
        "unit": unit,
        "base_unit_qty": base_qty,
    }


def validate_price(data, *, product_ids, store_ids):
    errors = {}
    try:
        product_id = parse_int(data.get("product_id"), "product")
        if product_id not in product_ids:
            errors["product_id"] = "Product not found."
    except ValueError as exc:
        errors["product_id"] = str(exc)
        product_id = None
    try:
        store_id = parse_int(data.get("store_id"), "store")
        if store_id not in store_ids:
            errors["store_id"] = "Store not found."
    except ValueError as exc:
        errors["store_id"] = str(exc)
        store_id = None
    try:
        price = to_paise(data.get("price"))
    except ValueError as exc:
        errors["price"] = str(exc)
        price = None
    try:
        price_date = parse_date(data.get("date"))
    except ValueError as exc:
        errors["date"] = str(exc)
        price_date = None
    try:
        in_stock = parse_bool(data.get("in_stock"))
    except ValueError as exc:
        errors["in_stock"] = str(exc)
        in_stock = None
    fail(errors)
    return {
        "product_id": product_id,
        "store_id": store_id,
        "price": price,
        "date": price_date,
        "in_stock": in_stock,
    }


def validate_list_payload(data, *, product_ids, require_items=False):
    errors = {}
    name = _text(data, "name", errors, max_len=120)
    raw_items = data.get("items", [])
    if raw_items is None:
        raw_items = []
    if not isinstance(raw_items, list):
        errors["items"] = "Items must be a list."
        raw_items = []
    if require_items and not raw_items:
        errors["items"] = "Add at least one product."
    items = []
    seen = set()
    item_errors = []
    for index, raw in enumerate(raw_items):
        row_errors = {}
        if not isinstance(raw, dict):
            item_errors.append({"index": index, "error": "Each item must be an object."})
            continue
        try:
            product_id = parse_int(raw.get("product_id"), "product")
            if product_id not in product_ids:
                row_errors["product_id"] = "Product not found."
            elif product_id in seen:
                row_errors["product_id"] = "This product is already on the list."
            else:
                seen.add(product_id)
        except ValueError as exc:
            row_errors["product_id"] = str(exc)
            product_id = None
        try:
            quantity = parse_quantity(raw.get("quantity"))
        except ValueError as exc:
            row_errors["quantity"] = str(exc)
            quantity = None
        if row_errors:
            item_errors.append({"index": index, "fields": row_errors})
        elif product_id is not None and quantity is not None:
            items.append({"product_id": product_id, "quantity": quantity})
    if item_errors:
        errors["items"] = item_errors
    fail(errors)
    return {"name": name, "items": items}


def validate_budget(data, *, category_ids):
    errors = {}
    try:
        month = parse_month(data.get("month"))
    except ValueError as exc:
        errors["month"] = str(exc)
        month = None
    try:
        total = to_paise(data.get("total"))
    except ValueError as exc:
        errors["total"] = str(exc)
        total = None
    raw_limits = data.get("categories", [])
    if raw_limits is None:
        raw_limits = []
    if not isinstance(raw_limits, list):
        errors["categories"] = "Category limits must be a list."
        raw_limits = []
    limits = []
    seen = set()
    limit_errors = []
    for index, raw in enumerate(raw_limits):
        if not isinstance(raw, dict):
            limit_errors.append({"index": index, "error": "Each limit must be an object."})
            continue
        limit_value = raw.get("limit")
        if limit_value in (None, ""):
            continue
        row_errors = {}
        try:
            category_id = parse_int(raw.get("category_id"), "category")
            if category_id not in category_ids:
                row_errors["category_id"] = "Category not found."
            elif category_id in seen:
                row_errors["category_id"] = "Duplicate category."
            else:
                seen.add(category_id)
        except ValueError as exc:
            row_errors["category_id"] = str(exc)
            category_id = None
        try:
            limit_paise = to_paise(limit_value)
        except ValueError as exc:
            row_errors["limit"] = str(exc)
            limit_paise = None
        if row_errors:
            limit_errors.append({"index": index, "fields": row_errors})
        elif category_id is not None and limit_paise is not None:
            limits.append({"category_id": category_id, "limit_amount": limit_paise})
    if limit_errors:
        errors["categories"] = limit_errors
    fail(errors)
    return {"month": month, "total_amount": total, "categories": limits}


def validate_max_stores(value) -> int:
    try:
        number = int(value)
    except (TypeError, ValueError) as exc:
        raise ValidationError(
            "Validation failed", {"fields": {"max_stores": "Choose 1, 2, or 3 stores."}}
        ) from exc
    if number not in (1, 2, 3):
        raise ValidationError(
            "Validation failed", {"fields": {"max_stores": "Choose 1, 2, or 3 stores."}}
        )
    return number
