"""Latest and historical shelf prices."""

from app.extensions import db
from app.models import Price


def latest_price_rows(product_ids=None):
    grouped = db.session.query(
        Price.product_id.label("product_id"),
        Price.store_id.label("store_id"),
        db.func.max(Price.date).label("max_date"),
    )
    if product_ids is not None:
        grouped = grouped.filter(Price.product_id.in_(list(product_ids) or [-1]))
    sub = grouped.group_by(Price.product_id, Price.store_id).subquery()
    return (
        db.session.query(Price)
        .join(
            sub,
            (Price.product_id == sub.c.product_id)
            & (Price.store_id == sub.c.store_id)
            & (Price.date == sub.c.max_date),
        )
        .all()
    )


def latest_by_product(product_ids=None):
    grouped = {}
    for row in latest_price_rows(product_ids):
        grouped.setdefault(row.product_id, []).append(row)
    return grouped
