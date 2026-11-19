"""Monthly budget maths, warnings, and fit-to-budget suggestions."""

import calendar
from datetime import date
from decimal import Decimal, ROUND_CEILING, ROUND_HALF_UP

from app.extensions import db
from app.models import Budget, Category, CategoryBudget, Expense, Product, ShoppingList
from app.services.estimator import _stores, basket_from_products, estimate_list
from app.services.optimizer import optimize
from app.services.pricing import latest_by_product
from app.services.units import as_decimal, line_total_paise, per_unit_paise, unit_suffix
from app.utils.errors import ApiError
from app.utils.money import chart_amount, format_money
from app.utils.validation import parse_month


def month_bounds(month: str) -> tuple[date, date]:
    year, month_number = map(int, parse_month(month).split("-"))
    last_day = calendar.monthrange(year, month_number)[1]
    return date(year, month_number, 1), date(year, month_number, last_day)


def month_label(month: str) -> str:
    start, _end = month_bounds(month)
    return f"{calendar.month_name[start.month]} {start.year}"


def date_within_month(month: str, today: date | None = None) -> date:
    today = today or date.today()
    start, end = month_bounds(month)
    if today < start:
        return start
    if today > end:
        return end
    return today


def project_month_end(actual_paise: int, month: str, as_of: date) -> int:
    start, end = month_bounds(month)
    if as_of < start:
        return 0
    if as_of >= end:
        return int(actual_paise)
    days_elapsed = (as_of - start).days + 1
    days_total = (end - start).days + 1
    projected = (Decimal(int(actual_paise)) * Decimal(days_total) / Decimal(days_elapsed)).quantize(
        Decimal("1"), rounding=ROUND_HALF_UP
    )
    return int(projected)


def plain_amount(paise: int) -> str:
    return f"{Decimal(int(paise)) / Decimal(100):.2f}"


def percent_used(part: int, whole: int):
    if whole <= 0:
        return None
    return float(
        (Decimal(int(part)) * Decimal(100) / Decimal(int(whole))).quantize(
            Decimal("0.1"), rounding=ROUND_HALF_UP
        )
    )


def progress_tone(percent) -> str:
    if percent is None:
        return "ok"
    if percent > 100:
        return "over"
    if percent > 80:
        return "warning"
    return "ok"


def build_warnings(total_paise: int | None, committed_paise: int, categories: list[dict]) -> list[dict]:
    warnings = []
    if total_paise and total_paise > 0:
        ratio = Decimal(int(committed_paise)) / Decimal(int(total_paise))
        if ratio > 1:
            over = int(committed_paise) - int(total_paise)
            warnings.append(
                {
                    "code": "total_over",
                    "level": "over",
                    "message": f"You are over your total budget by {format_money(over)}.",
                }
            )
        elif ratio > Decimal("0.8"):
            shown = percent_used(committed_paise, total_paise)
            warnings.append(
                {
                    "code": "total_high",
                    "level": "warning",
                    "message": f"You have used {shown}% of your total budget.",
                }
            )
    for category in categories:
        limit = category.get("limit_paise")
        if not limit:
            continue
        spent = int(category["committed_paise"])
        ratio = Decimal(spent) / Decimal(int(limit))
        name = category["name"]
        if ratio > 1:
            over = spent - int(limit)
            warnings.append(
                {
                    "code": "category_over",
                    "level": "over",
                    "category_id": category["category_id"],
                    "message": f"{name} is over its limit by {format_money(over)}.",
                }
            )
        elif ratio > Decimal("0.8"):
            shown = percent_used(spent, limit)
            warnings.append(
                {
                    "code": "category_high",
                    "level": "warning",
                    "category_id": category["category_id"],
                    "message": f"{name} has used {shown}% of its category limit.",
                }
            )
    return warnings


def summarize(month: str, as_of: date | None = None) -> dict:
    month = parse_month(month)
    as_of = as_of or date.today()
    start, end = month_bounds(month)
    budget = Budget.query.filter_by(month=month).first()
    expenses = (
        Expense.query.filter(Expense.date >= start, Expense.date <= end).order_by(Expense.date, Expense.id).all()
    )
    actual = sum(row.amount for row in expenses if row.status == "actual")
    planned = sum(row.amount for row in expenses if row.status == "planned")
    committed = actual + planned
    total = int(budget.total_amount) if budget else None
    remaining = None if total is None else total - committed
    projected = project_month_end(actual, month, as_of)
    limits = {}
    if budget:
        limits = {row.category_id: int(row.limit_amount) for row in budget.category_limits}
    spent = {}
    for row in expenses:
        if row.category_id is None:
            continue
        bucket = spent.setdefault(row.category_id, {"actual": 0, "planned": 0})
        bucket[row.status] += int(row.amount)
    categories = []
    for category in Category.query.order_by(Category.name).all():
        bucket = spent.get(category.id, {"actual": 0, "planned": 0})
        committed_cat = bucket["actual"] + bucket["planned"]
        limit = limits.get(category.id)
        categories.append(
            {
                "category_id": category.id,
                "name": category.name,
                "actual_paise": bucket["actual"],
                "actual_display": format_money(bucket["actual"]),
                "planned_paise": bucket["planned"],
                "planned_display": format_money(bucket["planned"]),
                "committed_paise": committed_cat,
                "committed_display": format_money(committed_cat),
                "limit_paise": limit,
                "limit_display": format_money(limit) if limit else None,
                "limit_input": plain_amount(limit) if limit else "",
                "percent_used": percent_used(committed_cat, limit) if limit else None,
            }
        )
    percent = percent_used(committed, total) if total else None
    chart_rows = [row for row in categories if row["committed_paise"] or row["limit_paise"]]
    return {
        "month": month,
        "month_label": month_label(month),
        "as_of": as_of.isoformat(),
        "budget_set": budget is not None,
        "total_paise": total,
        "total_display": format_money(total) if total is not None else None,
        "total_input": plain_amount(total) if total is not None else "",
        "actual_paise": actual,
        "actual_display": format_money(actual),
        "planned_paise": planned,
        "planned_display": format_money(planned),
        "committed_paise": committed,
        "committed_display": format_money(committed),
        "remaining_paise": remaining,
        "remaining_display": format_money(remaining) if remaining is not None else None,
        "percent_used": percent,
        "progress_tone": progress_tone(percent),
        "projected_paise": projected,
        "projected_display": format_money(projected),
        "projection_note": "Projected month-end spend follows the pace of actual expenses only.",
        "warnings": build_warnings(total, committed, categories),
        "categories": categories,
        "chart": {
            "labels": [row["name"] for row in chart_rows],
            "values": [chart_amount(row["committed_paise"]) for row in chart_rows],
            "displays": [row["committed_display"] for row in chart_rows],
            "limits": [chart_amount(row["limit_paise"]) if row["limit_paise"] else None for row in chart_rows],
            "limit_displays": [row["limit_display"] for row in chart_rows],
        },
        "expenses": [row.to_dict() for row in expenses],
    }


def save_budget(payload: dict) -> Budget:
    budget = Budget.query.filter_by(month=payload["month"]).first()
    if budget is None:
        budget = Budget(month=payload["month"], total_amount=payload["total_amount"])
        db.session.add(budget)
        db.session.flush()
    else:
        budget.total_amount = payload["total_amount"]
        for row in list(budget.category_limits):
            db.session.delete(row)
        db.session.flush()
    for limit in payload["categories"]:
        db.session.add(
            CategoryBudget(
                budget_id=budget.id,
                category_id=limit["category_id"],
                limit_amount=limit["limit_amount"],
            )
        )
    db.session.commit()
    return budget


def record_basket(month: str, shopping_list: ShoppingList, strategy_key: str, max_stores: int, status: str) -> dict:
    if strategy_key not in {"cheapest_single", "cheapest_split", "nearest"}:
        raise ApiError("Choose a strategy.", 422, {"fields": {"strategy": "Unknown strategy."}})
    if status not in {"planned", "actual"}:
        raise ApiError("Status must be planned or actual.", 422, {"fields": {"status": "Use planned or actual."}})
    plan = estimate_list(shopping_list, max_stores)
    strategy = plan["strategies"][strategy_key]
    if not strategy["complete"]:
        raise ApiError(
            "This strategy cannot buy every item.",
            422,
            {"missing": strategy["missing"]},
        )
    spent_on = date_within_month(month)
    created = []
    for line in strategy["lines"]:
        expense = Expense(
            date=spent_on,
            list_id=shopping_list.id,
            product_id=line["product_id"],
            store_id=line["store_id"],
            amount=line["line_paise"],
            category_id=line["category_id"],
            status=status,
        )
        db.session.add(expense)
        created.append(expense)
    for store in strategy["stores_used"]:
        if store["delivery_paise"] <= 0:
            continue
        expense = Expense(
            date=spent_on,
            list_id=shopping_list.id,
            product_id=None,
            store_id=store["id"],
            amount=store["delivery_paise"],
            category_id=None,
            status=status,
        )
        db.session.add(expense)
        created.append(expense)
    db.session.commit()
    return {
        "month": parse_month(month),
        "date": spent_on.isoformat(),
        "status": status,
        "strategy": strategy_key,
        "total_paise": strategy["total_paise"],
        "total_display": strategy["total_display"],
        "expenses": [row.to_dict() for row in created],
    }


def _packs_needed(needed_base: Decimal, pack_base: Decimal) -> Decimal:
    packs = (needed_base / pack_base).to_integral_value(rounding=ROUND_CEILING)
    if packs < 1:
        return Decimal("1")
    return packs


def suggest_adjustments(*, lines, alternatives, remaining_paise, basket_total_paise, complete: bool) -> dict:
    """Suggest swaps and cuts. Totals are computed here and returned to the client."""
    over_by = max(0, int(basket_total_paise) - int(remaining_paise))
    if complete and basket_total_paise <= remaining_paise:
        return {
            "within_budget": True,
            "complete": True,
            "over_by_paise": 0,
            "over_by_display": format_money(0),
            "suggestions": [],
        }
    suggestions = []
    present_ids = {int(line["product_id"]) for line in lines}
    for line in lines:
        if not line.get("available"):
            continue
        quantity = as_decimal(line["quantity"])
        current = int(line["line_paise"])
        category_id = line["category_id"]
        per_unit = line.get("per_unit_paise")
        if per_unit is None and line.get("unit_price_paise") is not None:
            per_unit = per_unit_paise(line["unit_price_paise"], line["base_unit_qty"])
        needed = as_decimal(line["base_unit_qty"]) * quantity
        for alt in alternatives:
            if alt["category_id"] != category_id or alt["product_id"] in present_ids:
                continue
            if per_unit is None or alt["per_unit_paise"] >= per_unit:
                continue
            alt_qty = _packs_needed(needed, as_decimal(alt["base_unit_qty"]))
            alt_cost = line_total_paise(alt["pack_price_paise"], alt_qty)
            if alt_cost >= current:
                continue
            new_total = int(basket_total_paise) - current + alt_cost
            suggestions.append(
                {
                    "type": "swap",
                    "title": f"Swap {line['name']} for {alt['brand']} {alt['name']}",
                    "detail": (
                        f"Buy {format(alt_qty, 'f')} × {alt['pack_size']} at {format_money(alt['pack_price_paise'])} "
                        f"({format_money(alt['per_unit_paise'])}/{unit_suffix(alt['unit'])} at {alt['store_name']})."
                    ),
                    "new_total_paise": new_total,
                    "saves_paise": int(basket_total_paise) - new_total,
                    "changes": [
                        {
                            "product_id": line["product_id"],
                            "new_product_id": alt["product_id"],
                            "quantity": format(alt_qty, "f"),
                        }
                    ],
                }
            )
        if quantity > 1:
            new_qty = quantity - 1
            new_line = line_total_paise(line["unit_price_paise"], new_qty)
            new_total = int(basket_total_paise) - current + new_line
            suggestions.append(
                {
                    "type": "reduce",
                    "title": f"Reduce {line['name']} to {format(new_qty, 'f')}",
                    "detail": f"The line falls from {format_money(current)} to {format_money(new_line)}.",
                    "new_total_paise": new_total,
                    "saves_paise": current - new_line,
                    "changes": [
                        {
                            "product_id": line["product_id"],
                            "new_product_id": line["product_id"],
                            "quantity": format(new_qty, "f"),
                        }
                    ],
                }
            )
        if current > 0:
            new_total = int(basket_total_paise) - current
            suggestions.append(
                {
                    "type": "remove",
                    "title": f"Remove {line['name']}",
                    "detail": f"This drops {format_money(current)} from the basket.",
                    "new_total_paise": new_total,
                    "saves_paise": current,
                    "changes": [
                        {
                            "product_id": line["product_id"],
                            "new_product_id": line["product_id"],
                            "quantity": "0",
                        }
                    ],
                }
            )
    decorated = []
    for suggestion in suggestions:
        within = complete and suggestion["new_total_paise"] <= int(remaining_paise)
        decorated.append(
            {
                **suggestion,
                "new_total_display": format_money(suggestion["new_total_paise"]),
                "saves_display": format_money(suggestion["saves_paise"]),
                "within_budget": within,
            }
        )
    decorated.sort(key=lambda row: (not row["within_budget"], row["new_total_paise"], row["type"]))
    # Keep the strongest few of each kind so one cheap removal does not hide swaps.
    kept = []
    counts = {"swap": 0, "reduce": 0, "remove": 0}
    caps = {"swap": 3, "reduce": 3, "remove": 2}
    for row in decorated:
        if counts[row["type"]] >= caps[row["type"]]:
            continue
        counts[row["type"]] += 1
        kept.append(row)
    return {
        "within_budget": False,
        "complete": complete,
        "over_by_paise": over_by if complete else None,
        "over_by_display": format_money(over_by) if complete else None,
        "suggestions": kept,
    }


def _alternatives(category_ids: set[int]) -> list[dict]:
    products = Product.query.filter(Product.category_id.in_(category_ids or [-1])).all()
    prices = latest_by_product([product.id for product in products])
    stores = {store.id: store for store in _stores()}
    found = []
    for product in products:
        best = None
        for row in prices.get(product.id, []):
            if not row.in_stock:
                continue
            per_unit = per_unit_paise(row.price, product.base_unit_qty)
            store = stores.get(row.store_id)
            distance = as_decimal(store.distance_km) if store else Decimal("999")
            candidate = (per_unit, int(row.price), distance, row.store_id)
            if best is None or candidate < best[0]:
                best = (candidate, row, store)
        if best is None:
            continue
        (_key, row, store) = best
        per_unit = per_unit_paise(row.price, product.base_unit_qty)
        found.append(
            {
                "product_id": product.id,
                "name": product.name,
                "brand": product.brand,
                "pack_size": product.pack_size,
                "category_id": product.category_id,
                "unit": product.unit,
                "base_unit_qty": format(as_decimal(product.base_unit_qty), "f"),
                "pack_price_paise": int(row.price),
                "per_unit_paise": per_unit,
                "store_name": store.name if store else "",
            }
        )
    return found


def fit_list(shopping_list: ShoppingList, month: str, max_stores: int) -> dict:
    try:
        month = parse_month(month)
    except ValueError as exc:
        raise ApiError("Validation failed", 422, {"fields": {"month": str(exc)}}) from exc
    budget = Budget.query.filter_by(month=month).first()
    if budget is None:
        raise ApiError("Set a budget for this month first.", 422, {"fields": {"month": "No budget for this month."}})
    summary = summarize(month)
    plan = estimate_list(shopping_list, max_stores)
    key = plan["recommended_key"] or "cheapest_split"
    strategy = plan["strategies"][key]
    alternatives = _alternatives({line["category_id"] for line in strategy["lines"] if line["category_id"]})
    advice = suggest_adjustments(
        lines=strategy["lines"],
        alternatives=alternatives,
        remaining_paise=summary["remaining_paise"],
        basket_total_paise=strategy["total_paise"],
        complete=strategy["complete"],
    )
    advice.update(
        {
            "month": month,
            "list_id": shopping_list.id,
            "strategy": key,
            "basket_total_paise": strategy["total_paise"],
            "basket_total_display": strategy["total_display"],
            "remaining_paise": summary["remaining_paise"],
            "remaining_display": summary["remaining_display"],
            "missing": strategy["missing"],
        }
    )
    if not strategy["complete"]:
        advice["message"] = "Some items are unavailable in this plan, so the total does not cover the whole list."
    elif advice["within_budget"]:
        advice["message"] = "This basket fits the remaining budget."
    else:
        advice["message"] = f"This basket is over the remaining budget by {advice['over_by_display']}."
    return advice


def reference_plan(pairs):
    """Price an arbitrary basket. Used by insights for the staples list."""
    stores = _stores()
    items = basket_from_products(pairs)
    return optimize(stores, items, max_stores=1)
