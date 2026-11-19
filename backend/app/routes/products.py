"""Product, category, and config endpoints."""

from datetime import date

from flask import Blueprint, current_app, jsonify, request

from app.extensions import db
from app.models import Category, Price, Product, ShoppingListItem
from app.services import catalog
from app.utils.errors import ApiError
from app.utils.validation import json_body, validate_product

bp = Blueprint("products", __name__, url_prefix="/api")

SORTS = {"name_asc", "name_desc", "price_asc", "price_desc", "unit_price_asc", "unit_price_desc"}


def _product_or_404(product_id: int) -> Product:
    product = db.session.get(Product, product_id)
    if product is None:
        raise ApiError("Product not found", 404)
    return product


@bp.get("/config")
def config():
    today = date.today()
    return jsonify(
        {
            "currency_symbol": current_app.config["CURRENCY_SYMBOL"],
            "currency_code": current_app.config["CURRENCY_CODE"],
            "decimal_places": current_app.config["DECIMAL_PLACES"],
            "thousands_separator": current_app.config["THOUSANDS_SEPARATOR"],
            "paise_per_unit": current_app.config["PAISE_PER_UNIT"],
            "server_date": today.isoformat(),
            "default_month": today.strftime("%Y-%m"),
        }
    )


@bp.get("/categories")
def categories():
    return jsonify({"categories": catalog.list_categories()})


@bp.post("/categories")
def create_category():
    data = json_body()
    name = data.get("name")
    if not isinstance(name, str) or not name.strip():
        raise ApiError("Validation failed", 422, {"fields": {"name": "Enter a category name."}})
    name = name.strip()
    if len(name) > 80:
        raise ApiError("Validation failed", 422, {"fields": {"name": "Use at most 80 characters."}})
    if Category.query.filter_by(name=name).first():
        raise ApiError("That category already exists.", 409)
    category = Category(name=name)
    db.session.add(category)
    db.session.commit()
    return jsonify(category.to_dict()), 201


@bp.get("/brands")
def brands():
    return jsonify({"brands": catalog.list_brands()})


@bp.get("/products")
def products():
    try:
        page = int(request.args.get("page", 1))
        per_page = int(request.args.get("per_page", 30))
    except ValueError as exc:
        raise ApiError("Validation failed", 422, {"fields": {"page": "Page and per_page must be numbers."}}) from exc
    if page < 1:
        raise ApiError("Validation failed", 422, {"fields": {"page": "Page must be 1 or greater."}})
    per_page = min(max(per_page, 1), 300)
    sort = request.args.get("sort", "name_asc")
    if sort not in SORTS:
        raise ApiError("Validation failed", 422, {"fields": {"sort": "Unknown sort."}})
    category_id = request.args.get("category_id") or None
    if category_id is not None:
        try:
            category_id = int(category_id)
        except ValueError as exc:
            raise ApiError("Validation failed", 422, {"fields": {"category_id": "Invalid category."}}) from exc
    payload = catalog.search_products(
        q=request.args.get("q", ""),
        category_id=category_id,
        brand=request.args.get("brand", ""),
        sort=sort,
        page=page,
        per_page=per_page,
        in_stock_only=request.args.get("in_stock") == "1",
    )
    return jsonify(payload)


@bp.post("/products")
def create_product():
    category_ids = {row.id for row in Category.query.all()}
    clean = validate_product(json_body(), category_ids=category_ids)
    product = Product(**clean)
    db.session.add(product)
    db.session.commit()
    return jsonify(catalog.product_detail(product)), 201


@bp.get("/products/<int:product_id>")
def get_product(product_id):
    return jsonify(catalog.product_detail(_product_or_404(product_id)))


@bp.put("/products/<int:product_id>")
def update_product(product_id):
    product = _product_or_404(product_id)
    category_ids = {row.id for row in Category.query.all()}
    clean = validate_product(json_body(), category_ids=category_ids)
    for key, value in clean.items():
        setattr(product, key, value)
    db.session.commit()
    return jsonify(catalog.product_detail(product))


@bp.delete("/products/<int:product_id>")
def delete_product(product_id):
    product = _product_or_404(product_id)
    if Price.query.filter_by(product_id=product.id).first() or ShoppingListItem.query.filter_by(product_id=product.id).first():
        raise ApiError("Remove prices and list lines that use this product first.", 422)
    db.session.delete(product)
    db.session.commit()
    return jsonify({"deleted": product_id})


@bp.get("/products/<int:product_id>/prices")
def product_prices(product_id):
    return jsonify(catalog.price_history(_product_or_404(product_id)))
