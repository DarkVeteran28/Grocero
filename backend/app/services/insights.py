"""Reference basket, monthly price drops, and savings reconstructed from expenses."""

import calendar
from collections import defaultdict
from datetime import date
from decimal import Decimal, ROUND_HALF_UP

from app.config import DATA_DIR
from app.extensions import db
from app.models import Expense, Price, Product, Store
from app.services.budget import reference_plan
from app.services.estimator import _present_strategy
from app.services.units import as_decimal
from app.utils.money import chart_amount, format_money


def _sample_pairs(name: str):
    from app.services.csv_importer import read_sample_lists

    samples = read_sample_lists(DATA_DIR)
    sample = next((row for row in samples if row["name"] == name), None)
    if sample is None:
        return []
    products = {row.id: row for row in Product.query.filter(Product.id.in_([item["product_id"] for item in sample["items"]]))}
    pairs = []
    for item in sample["items"]:
        product = products.get(item["product_id"])
        if product is None:
            continue
        pairs.append((product, as_decimal(item["quantity"])))
    return pairs


def _drops(period_start: date, period_end: date) -> list[dict]:
    rows = (
        Price.query.filter(Price.date >= period_start, Price.date <= period_end)
        .order_by(Price.product_id, Price.store_id, Price.date)
        .all()
    )
    grouped = defaultdict(list)
    for row in rows:
        grouped[(row.product_id, row.store_id)].append(row)
    products = {row.id: row for row in Product.query.all()}
    stores = {row.id: row for row in Store.query.all()}
    drops = []
    for (product_id, store_id), points in grouped.items():
        first, last = points[0], points[-1]
        if last.date == first.date or last.price >= first.price:
            continue
        drop = int(first.price) - int(last.price)
        percent = (Decimal(drop) * Decimal(100) / Decimal(int(first.price))).quantize(
            Decimal("0.1"), rounding=ROUND_HALF_UP
        )
        product = products.get(product_id)
        store = stores.get(store_id)
        product_name = product.name if product else f"Product {product_id}"
        brand = product.brand if product else ""
        store_name = store.name if store else f"Store {store_id}"
        drops.append(
            {
                "product_id": product_id,
                "name": product_name,
                "brand": brand,
                "pack_size": product.pack_size if product else "",
                "store_id": store_id,
                "store_name": store_name,
                "old_paise": int(first.price),
                "old_display": format_money(first.price),
                "new_paise": int(last.price),
                "new_display": format_money(last.price),
                "drop_paise": drop,
                "drop_display": format_money(drop),
                "drop_percent": float(percent),
                "from_date": first.date.isoformat(),
                "to_date": last.date.isoformat(),
            }
        )
    drops.sort(key=lambda row: (-row["drop_paise"], row["name"]))
    return drops[:8]


def _savings_achieved() -> dict:
    expenses = Expense.query.filter_by(status="actual").filter(Expense.product_id.isnot(None)).all()
    total = 0
    counted = 0
    for expense in expenses:
        if expense.store_id is None:
            continue
        same_day = Price.query.filter_by(product_id=expense.product_id, date=expense.date).all()
        paid = next((row for row in same_day if row.store_id == expense.store_id), None)
        if paid is None or not same_day:
            continue
        most = max(int(row.price) for row in same_day)
        unit = int(paid.price)
        if unit <= 0:
            continue
        quantity = (Decimal(int(expense.amount)) / Decimal(unit)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        saved = int(((Decimal(most - unit) * quantity).quantize(Decimal("1"), rounding=ROUND_HALF_UP)))
        if saved > 0:
            total += saved
            counted += 1
    return {
        "total_paise": total,
        "total_display": format_money(total),
        "lines_compared": counted,
        "note": "Savings compare each recorded actual item with the most expensive store on that date.",
    }


def build_insights() -> dict:
    latest = db.session.query(db.func.max(Price.date)).scalar()
    if latest is None:
        period = date.today().strftime("%Y-%m")
        start = date.today().replace(day=1)
        end = start
    else:
        start = latest.replace(day=1)
        end = latest
        period = start.strftime("%Y-%m")
    pairs = _sample_pairs("Monthly family staples")
    cheapest = None
    if pairs and Store.query.count():
        plan = reference_plan(pairs)
        strategy = plan["strategies"]["cheapest_single"]
        most = plan["most_expensive"]
        presented = _present_strategy(strategy)
        most_presented = _present_strategy(most) if most else None
        store = presented["stores_used"][0] if presented["stores_used"] else None
        cheapest = {
            "basket_name": "Monthly family staples",
            "complete": presented["complete"],
            "store_id": store["id"] if store else None,
            "store_name": store["name"] if store else None,
            "total_paise": presented["total_paise"],
            "total_display": presented["total_display"],
            "delivery_display": presented["delivery_display"],
            "most_expensive_store": most_presented["stores_used"][0]["name"] if most_presented and most_presented["stores_used"] else None,
            "most_expensive_display": most_presented["total_display"] if most_presented else None,
            "savings_display": presented["savings_display"],
            "missing": presented["missing"],
        }
    drops = _drops(start, end) if latest else []
    return {
        "period": period,
        "period_label": f"{calendar.month_name[start.month]} {start.year}",
        "cheapest_store": cheapest,
        "price_drops": drops,
        "drop_chart": {
            "labels": [f"{row['name']} · {row['store_name']}"[:48] for row in drops],
            "values": [chart_amount(row["drop_paise"]) for row in drops],
            "displays": [row["drop_display"] for row in drops],
        },
        "savings_achieved": _savings_achieved(),
        "counts": {
            "products": Product.query.count(),
            "stores": Store.query.count(),
            "prices": Price.query.count(),
        },
    }
