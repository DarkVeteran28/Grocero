"""Budgets, the month dashboard, and recording a basket."""

from datetime import datetime

from flask import Blueprint, jsonify, request

from app.extensions import db
from app.models import Budget, Category, Expense, ShoppingList
from app.services.budget import record_basket, save_budget, summarize
from app.utils.errors import ApiError
from app.utils.validation import json_body, parse_month, validate_budget, validate_max_stores

bp = Blueprint("budgets", __name__, url_prefix="/api")


def _as_of():
    raw = request.args.get("as_of")
    if not raw:
        return None
    try:
        return datetime.strptime(raw, "%Y-%m-%d").date()
    except ValueError as exc:
        raise ApiError("Validation failed", 422, {"fields": {"as_of": "Use YYYY-MM-DD."}}) from exc


@bp.get("/budgets")
def budgets():
    rows = []
    for budget in Budget.query.order_by(Budget.month).all():
        rows.append(
            {
                "month": budget.month,
                "total_paise": budget.total_amount,
                "category_limits": [
                    {"category_id": limit.category_id, "limit_paise": limit.limit_amount}
                    for limit in budget.category_limits
                ],
            }
        )
    return jsonify({"budgets": rows})


@bp.post("/budgets")
def create_budget():
    data = json_body()
    try:
        month = parse_month(data.get("month"))
    except ValueError as exc:
        raise ApiError("Validation failed", 422, {"fields": {"month": str(exc)}}) from exc
    if Budget.query.filter_by(month=month).first():
        raise ApiError("A budget for that month already exists.", 409)
    category_ids = {row.id for row in Category.query.with_entities(Category.id)}
    payload = validate_budget(data, category_ids=category_ids)
    budget = save_budget(payload)
    return jsonify(summarize(budget.month, _as_of())), 201


@bp.put("/budgets/<string:month>")
def update_budget(month):
    try:
        month = parse_month(month)
    except ValueError as exc:
        raise ApiError("Validation failed", 422, {"fields": {"month": str(exc)}}) from exc
    data = json_body()
    data["month"] = month
    category_ids = {row.id for row in Category.query.with_entities(Category.id)}
    payload = validate_budget(data, category_ids=category_ids)
    save_budget(payload)
    return jsonify(summarize(month, _as_of()))


@bp.delete("/budgets/<string:month>")
def delete_budget(month):
    try:
        month = parse_month(month)
    except ValueError as exc:
        raise ApiError("Validation failed", 422, {"fields": {"month": str(exc)}}) from exc
    budget = Budget.query.filter_by(month=month).first()
    if budget is None:
        raise ApiError("Budget not found", 404)
    db.session.delete(budget)
    db.session.commit()
    return jsonify({"deleted": month})


@bp.get("/budgets/<string:month>/summary")
def summary(month):
    try:
        month = parse_month(month)
    except ValueError as exc:
        raise ApiError("Validation failed", 422, {"fields": {"month": str(exc)}}) from exc
    return jsonify(summarize(month, _as_of()))


@bp.post("/budgets/<string:month>/expenses")
def create_expenses(month):
    try:
        month = parse_month(month)
    except ValueError as exc:
        raise ApiError("Validation failed", 422, {"fields": {"month": str(exc)}}) from exc
    data = json_body()
    try:
        list_id = int(data.get("list_id"))
    except (TypeError, ValueError) as exc:
        raise ApiError("Validation failed", 422, {"fields": {"list_id": "Choose a list."}}) from exc
    shopping_list = db.session.get(ShoppingList, list_id)
    if shopping_list is None:
        raise ApiError("List not found", 404)
    max_stores = validate_max_stores(data.get("max_stores", 3))
    created = record_basket(month, shopping_list, data.get("strategy"), max_stores, data.get("status"))
    return jsonify(created), 201


@bp.delete("/budgets/<string:month>/expenses/<int:expense_id>")
def delete_expense(month, expense_id):
    try:
        parse_month(month)
    except ValueError as exc:
        raise ApiError("Validation failed", 422, {"fields": {"month": str(exc)}}) from exc
    expense = db.session.get(Expense, expense_id)
    if expense is None:
        raise ApiError("Expense not found", 404)
    db.session.delete(expense)
    db.session.commit()
    return jsonify({"deleted": expense_id})
