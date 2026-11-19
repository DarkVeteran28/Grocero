"""Monthly budgets and recorded grocery expenses."""

from app.extensions import db
from app.utils.money import format_money


class Budget(db.Model):
    __tablename__ = "budgets"

    id = db.Column(db.Integer, primary_key=True)
    month = db.Column(db.String(7), nullable=False, unique=True)
    total_amount = db.Column(db.Integer, nullable=False)

    category_limits = db.relationship(
        "CategoryBudget",
        back_populates="budget",
        cascade="all, delete-orphan",
    )

    __table_args__ = (db.CheckConstraint("total_amount > 0", name="ck_budget_total_positive"),)


class CategoryBudget(db.Model):
    __tablename__ = "category_budgets"

    id = db.Column(db.Integer, primary_key=True)
    budget_id = db.Column(db.Integer, db.ForeignKey("budgets.id", ondelete="CASCADE"), nullable=False)
    category_id = db.Column(db.Integer, db.ForeignKey("categories.id"), nullable=False)
    limit_amount = db.Column(db.Integer, nullable=False)

    budget = db.relationship("Budget", back_populates="category_limits")
    category = db.relationship("Category")

    __table_args__ = (
        db.UniqueConstraint("budget_id", "category_id", name="uq_budget_category"),
        db.CheckConstraint("limit_amount > 0", name="ck_category_budget_positive"),
    )


class Expense(db.Model):
    __tablename__ = "expenses"

    id = db.Column(db.Integer, primary_key=True)
    date = db.Column(db.Date, nullable=False, index=True)
    list_id = db.Column(db.Integer, db.ForeignKey("shopping_lists.id", ondelete="SET NULL"), nullable=True)
    product_id = db.Column(db.Integer, db.ForeignKey("products.id"), nullable=True)
    store_id = db.Column(db.Integer, db.ForeignKey("stores.id"), nullable=True)
    amount = db.Column(db.Integer, nullable=False)
    category_id = db.Column(db.Integer, db.ForeignKey("categories.id"), nullable=True)
    status = db.Column(db.String(16), nullable=False)

    product = db.relationship("Product")
    store = db.relationship("Store")
    category = db.relationship("Category")

    __table_args__ = (
        db.CheckConstraint("amount > 0", name="ck_expense_amount_positive"),
        db.CheckConstraint("status IN ('planned', 'actual')", name="ck_expense_status"),
    )

    def to_dict(self):
        return {
            "id": self.id,
            "date": self.date.isoformat(),
            "list_id": self.list_id,
            "product_id": self.product_id,
            "product_name": self.product.name if self.product else None,
            "store_id": self.store_id,
            "store_name": self.store.name if self.store else None,
            "category_id": self.category_id,
            "category_name": self.category.name if self.category else None,
            "amount_paise": self.amount,
            "amount_display": format_money(self.amount),
            "status": self.status,
            "kind": "delivery" if self.product_id is None else "item",
        }
