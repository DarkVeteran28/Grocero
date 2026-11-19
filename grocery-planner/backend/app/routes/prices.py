"""Shelf-price maintenance and CSV import."""

from flask import Blueprint, jsonify, request

from app.extensions import db
from app.models import Price, Product, Store
from app.services.csv_importer import apply_price_rows, parse_price_csv
from app.utils.errors import ApiError
from app.utils.validation import json_body, validate_price

bp = Blueprint("prices", __name__, url_prefix="/api")


def _ids():
    return (
        {row.id for row in Product.query.with_entities(Product.id)},
        {row.id for row in Store.query.with_entities(Store.id)},
    )


@bp.get("/prices")
def prices():
    query = Price.query
    product_id = request.args.get("product_id")
    store_id = request.args.get("store_id")
    try:
        if product_id:
            query = query.filter(Price.product_id == int(product_id))
        if store_id:
            query = query.filter(Price.store_id == int(store_id))
    except ValueError as exc:
        raise ApiError("Validation failed", 422, {"fields": {"id": "Product and store ids must be numbers."}}) from exc
    try:
        limit = min(max(int(request.args.get("limit", 30)), 1), 200)
    except ValueError as exc:
        raise ApiError("Validation failed", 422, {"fields": {"limit": "Limit must be a number."}}) from exc
    rows = query.order_by(Price.date.desc(), Price.id.desc()).limit(limit).all()
    return jsonify({"prices": [row.to_dict() for row in rows]})


@bp.post("/prices")
def create_price():
    product_ids, store_ids = _ids()
    clean = validate_price(json_body(), product_ids=product_ids, store_ids=store_ids)
    existing = Price.query.filter_by(
        product_id=clean["product_id"], store_id=clean["store_id"], date=clean["date"]
    ).first()
    if existing:
        existing.price = clean["price"]
        existing.in_stock = clean["in_stock"]
        db.session.commit()
        return jsonify(existing.to_dict())
    row = Price(**clean)
    db.session.add(row)
    db.session.commit()
    return jsonify(row.to_dict()), 201


@bp.put("/prices/<int:price_id>")
def update_price(price_id):
    row = db.session.get(Price, price_id)
    if row is None:
        raise ApiError("Price not found", 404)
    product_ids, store_ids = _ids()
    clean = validate_price(json_body(), product_ids=product_ids, store_ids=store_ids)
    for key, value in clean.items():
        setattr(row, key, value)
    db.session.commit()
    return jsonify(row.to_dict())


@bp.delete("/prices/<int:price_id>")
def delete_price(price_id):
    row = db.session.get(Price, price_id)
    if row is None:
        raise ApiError("Price not found", 404)
    db.session.delete(row)
    db.session.commit()
    return jsonify({"deleted": price_id})


@bp.post("/prices/import")
def import_prices():
    upload = request.files.get("file")
    if upload is None:
        text = request.get_data(as_text=True)
    else:
        text = upload.read().decode("utf-8-sig")
    if not text or not text.strip():
        raise ApiError("Choose a CSV file.", 422, {"fields": {"file": "The file is empty."}})
    product_ids, store_ids = _ids()
    rows, errors = parse_price_csv(text, product_ids, store_ids)
    if not rows and errors:
        return jsonify({"error": "No prices were imported.", "details": {"errors": errors}, "imported": 0, "updated": 0}), 422
    imported, updated = apply_price_rows(rows)
    return jsonify({"imported": imported, "updated": updated, "errors": errors})
