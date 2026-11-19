"""Categories and sellable packs."""

from app.extensions import db


class Category(db.Model):
    __tablename__ = "categories"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(80), nullable=False, unique=True)

    products = db.relationship("Product", back_populates="category")

    def to_dict(self):
        return {"id": self.id, "name": self.name}


class Product(db.Model):
    __tablename__ = "products"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(160), nullable=False)
    brand = db.Column(db.String(80), nullable=False)
    category_id = db.Column(db.Integer, db.ForeignKey("categories.id"), nullable=False, index=True)
    pack_size = db.Column(db.String(32), nullable=False)
    unit = db.Column(db.String(16), nullable=False)
    base_unit_qty = db.Column(db.Numeric(12, 4), nullable=False)

    category = db.relationship("Category", back_populates="products")

    __table_args__ = (db.CheckConstraint("base_unit_qty > 0", name="ck_products_base_qty_positive"),)

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "brand": self.brand,
            "category_id": self.category_id,
            "category_name": self.category.name if self.category is not None else None,
            "pack_size": self.pack_size,
            "unit": self.unit,
            "base_unit_qty": format(self.base_unit_qty, "f"),
        }
