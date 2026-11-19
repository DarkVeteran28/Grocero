"""Named shopping lists."""

from datetime import datetime, timezone

from app.extensions import db


def utcnow():
    return datetime.now(timezone.utc).replace(tzinfo=None)


class ShoppingList(db.Model):
    __tablename__ = "shopping_lists"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    created_at = db.Column(db.DateTime, nullable=False, default=utcnow)

    items = db.relationship(
        "ShoppingListItem",
        back_populates="shopping_list",
        cascade="all, delete-orphan",
        order_by="ShoppingListItem.id",
    )

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "item_count": len(self.items),
            "items": [item.to_dict() for item in self.items],
        }


class ShoppingListItem(db.Model):
    __tablename__ = "shopping_list_items"

    id = db.Column(db.Integer, primary_key=True)
    list_id = db.Column(
        db.Integer, db.ForeignKey("shopping_lists.id", ondelete="CASCADE"), nullable=False, index=True
    )
    product_id = db.Column(db.Integer, db.ForeignKey("products.id"), nullable=False, index=True)
    quantity = db.Column(db.Numeric(8, 2), nullable=False)

    shopping_list = db.relationship("ShoppingList", back_populates="items")
    product = db.relationship("Product")

    __table_args__ = (
        db.UniqueConstraint("list_id", "product_id", name="uq_list_product"),
        db.CheckConstraint("quantity > 0", name="ck_list_item_quantity_positive"),
    )

    def to_dict(self):
        product = self.product
        return {
            "id": self.id,
            "list_id": self.list_id,
            "product_id": self.product_id,
            "quantity": format(self.quantity, "f"),
            "product_name": product.name if product else None,
            "brand": product.brand if product else None,
            "pack_size": product.pack_size if product else None,
            "unit": product.unit if product else None,
            "category_id": product.category_id if product else None,
            "category_name": product.category.name if product and product.category else None,
        }
