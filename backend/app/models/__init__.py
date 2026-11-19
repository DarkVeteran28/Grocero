"""Import models so SQLAlchemy registers every table."""

from app.models.budget import Budget, CategoryBudget, Expense
from app.models.catalog import Category, Product
from app.models.price import Price
from app.models.shopping import ShoppingList, ShoppingListItem
from app.models.store import Store

__all__ = [
    "Budget",
    "Category",
    "CategoryBudget",
    "Expense",
    "Price",
    "Product",
    "ShoppingList",
    "ShoppingListItem",
    "Store",
]
