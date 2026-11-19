"""Store directory and maintenance."""

from flask import Blueprint, jsonify

from app.extensions import db
from app.models import Price, Store
from app.utils.errors import ApiError
from app.utils.validation import json_body, validate_store

bp = Blueprint("stores", __name__, url_prefix="/api")


def _store_or_404(store_id: int) -> Store:
    store = db.session.get(Store, store_id)
    if store is None:
        raise ApiError("Store not found", 404)
    return store


@bp.get("/stores")
def stores():
    rows = Store.query.order_by(Store.distance_km, Store.name).all()
    return jsonify({"stores": [row.to_dict() for row in rows]})


@bp.post("/stores")
def create_store():
    if Store.query.count() >= 12:
        raise ApiError("This planner compares at most 12 stores.", 422)
    store = Store(**validate_store(json_body()))
    db.session.add(store)
    db.session.commit()
    return jsonify(store.to_dict()), 201


@bp.put("/stores/<int:store_id>")
def update_store(store_id):
    store = _store_or_404(store_id)
    for key, value in validate_store(json_body()).items():
        setattr(store, key, value)
    db.session.commit()
    return jsonify(store.to_dict())


@bp.delete("/stores/<int:store_id>")
def delete_store(store_id):
    store = _store_or_404(store_id)
    if Price.query.filter_by(store_id=store.id).first():
        raise ApiError("Remove this store's prices first.", 422)
    db.session.delete(store)
    db.session.commit()
    return jsonify({"deleted": store_id})
