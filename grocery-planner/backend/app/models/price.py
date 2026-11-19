"""Dated shelf prices. The current price is the latest date for a product and store."""

from app.extensions import db
from app.utils.money import format_money


class Price(db.Model):
    __tablename__ = "prices"

    id = db.Column(db.Integer, primary_key=True)
    product_id = db.Column(db.Integer, db.ForeignKey("products.id"), nullable=False)
    store_id = db.Column(db.Integer, db.ForeignKey("stores.id"), nullable=False)
    price = db.Column(db.Integer, nullable=False)
    date = db.Column(db.Date, nullable=False)
    in_stock = db.Column(db.Boolean, nullable=False, default=True)

    product = db.relationship("Product")
    store = db.relationship("Store")

    __table_args__ = (
        db.UniqueConstraint("product_id", "store_id", "date", name="uq_price_product_store_date"),
        db.CheckConstraint("price > 0", name="ck_prices_price_positive"),
        db.Index("ix_prices_product_id", "product_id"),
        db.Index("ix_prices_store_id", "store_id"),
        db.Index("ix_prices_date", "date"),
        db.Index("ix_prices_product_store_date", "product_id", "store_id", "date"),
    )

    def to_dict(self):
        return {
            "id": self.id,
            "product_id": self.product_id,
            "store_id": self.store_id,
            "price_paise": self.price,
            "price_display": format_money(self.price),
            "date": self.date.isoformat(),
            "in_stock": bool(self.in_stock),
        }
