"""Store locations and delivery terms."""

from decimal import Decimal

from app.extensions import db
from app.utils.money import format_money


def _plain(paise: int) -> str:
    return f"{Decimal(int(paise)) / Decimal(100):.2f}"


class Store(db.Model):
    __tablename__ = "stores"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    type = db.Column(db.String(32), nullable=False)
    area = db.Column(db.String(80), nullable=False)
    distance_km = db.Column(db.Numeric(6, 2), nullable=False)
    delivery_fee = db.Column(db.Integer, nullable=False)
    free_delivery_above = db.Column(db.Integer, nullable=True)
    rating = db.Column(db.Numeric(2, 1), nullable=False)

    __table_args__ = (
        db.CheckConstraint("delivery_fee >= 0", name="ck_stores_delivery_nonnegative"),
        db.CheckConstraint("distance_km >= 0", name="ck_stores_distance_nonnegative"),
        db.CheckConstraint("rating >= 0 AND rating <= 5", name="ck_stores_rating_range"),
    )

    def to_dict(self):
        free = self.free_delivery_above
        return {
            "id": self.id,
            "name": self.name,
            "type": self.type,
            "area": self.area,
            "distance_km": format(self.distance_km, "f"),
            "distance_display": f"{format(self.distance_km, 'f')} km",
            "delivery_fee_paise": self.delivery_fee,
            "delivery_fee_display": format_money(self.delivery_fee),
            "delivery_fee_input": _plain(self.delivery_fee),
            "free_delivery_above_paise": free,
            "free_delivery_above_display": format_money(free) if free is not None else None,
            "free_delivery_above_input": None if free is None else _plain(free),
            "rating": format(self.rating, "f"),
        }
