"""Shopping lists, estimates, and applying a fit suggestion."""

from flask import Blueprint, current_app, jsonify, request

from app.config import DATA_DIR
from app.extensions import db
from app.models import Product, ShoppingList
from app.services.csv_importer import read_sample_lists
from app.services.estimator import estimate_list
from app.services.lists import apply_changes, copy_sample, save_list
from app.services.budget import fit_list
from app.utils.errors import ApiError
from app.utils.validation import json_body, validate_list_payload, validate_max_stores

bp = Blueprint("lists", __name__, url_prefix="/api")


def _list_or_404(list_id: int) -> ShoppingList:
    shopping_list = db.session.get(ShoppingList, list_id)
    if shopping_list is None:
        raise ApiError("List not found", 404)
    return shopping_list


def _product_ids():
    return {row.id for row in Product.query.with_entities(Product.id).all()}


@bp.get("/lists")
def lists():
    rows = ShoppingList.query.order_by(ShoppingList.id).all()
    return jsonify({"lists": [row.to_dict() for row in rows]})


@bp.post("/lists")
def create_list():
    payload = validate_list_payload(json_body(), product_ids=_product_ids())
    shopping_list = save_list(None, payload)
    return jsonify(shopping_list.to_dict()), 201


@bp.get("/lists/samples")
def samples():
    data_dir = current_app.config.get("DATA_DIR", DATA_DIR)
    from pathlib import Path

    return jsonify({"samples": read_sample_lists(Path(data_dir))})


@bp.post("/lists/samples")
def load_sample():
    data = json_body()
    name = data.get("name") or data.get("sample_name")
    if not isinstance(name, str) or not name.strip():
        raise ApiError("Validation failed", 422, {"fields": {"name": "Choose a sample list."}})
    from pathlib import Path

    found = next((row for row in read_sample_lists(Path(current_app.config["DATA_DIR"])) if row["name"] == name.strip()), None)
    if found is None:
        raise ApiError("Sample list not found", 404)
    shopping_list = copy_sample(found)
    return jsonify(shopping_list.to_dict()), 201


@bp.get("/lists/<int:list_id>")
def get_list(list_id):
    return jsonify(_list_or_404(list_id).to_dict())


@bp.put("/lists/<int:list_id>")
def update_list(list_id):
    shopping_list = _list_or_404(list_id)
    payload = validate_list_payload(json_body(), product_ids=_product_ids())
    return jsonify(save_list(shopping_list, payload).to_dict())


@bp.delete("/lists/<int:list_id>")
def delete_list(list_id):
    shopping_list = _list_or_404(list_id)
    db.session.delete(shopping_list)
    db.session.commit()
    return jsonify({"deleted": list_id})


@bp.post("/lists/<int:list_id>/estimate")
def estimate(list_id):
    data = request.get_json(silent=True) or {}
    if not isinstance(data, dict):
        raise ApiError("Expected a JSON object.", 422)
    max_stores = validate_max_stores(data.get("max_stores", 3))
    return jsonify(estimate_list(_list_or_404(list_id), max_stores))


@bp.post("/lists/<int:list_id>/fit")
def fit(list_id):
    data = json_body()
    month = data.get("month")
    max_stores = validate_max_stores(data.get("max_stores", 3))
    return jsonify(fit_list(_list_or_404(list_id), month, max_stores))


@bp.post("/lists/<int:list_id>/apply")
def apply_suggestion(list_id):
    data = json_body()
    shopping_list = apply_changes(_list_or_404(list_id), data.get("changes"))
    return jsonify(shopping_list.to_dict())
