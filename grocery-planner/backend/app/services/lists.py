"""Create and edit shopping lists."""

from decimal import Decimal

from app.extensions import db
from app.models import Product, ShoppingList, ShoppingListItem
from app.utils.errors import ApiError
from app.utils.validation import parse_quantity


def save_list(shopping_list: ShoppingList | None, payload: dict) -> ShoppingList:
    if shopping_list is None:
        shopping_list = ShoppingList(name=payload["name"])
        db.session.add(shopping_list)
        db.session.flush()
    else:
        shopping_list.name = payload["name"]
        for item in list(shopping_list.items):
            db.session.delete(item)
        db.session.flush()
    for item in payload["items"]:
        db.session.add(
            ShoppingListItem(
                list_id=shopping_list.id,
                product_id=item["product_id"],
                quantity=item["quantity"],
            )
        )
    db.session.commit()
    db.session.refresh(shopping_list)
    return shopping_list


def apply_changes(shopping_list: ShoppingList, changes: list[dict]) -> ShoppingList:
    if not isinstance(changes, list) or not changes:
        raise ApiError("Nothing to apply.", 422, {"fields": {"changes": "Choose a suggestion."}})
    by_product = {item.product_id: item for item in shopping_list.items}
    for change in changes:
        if not isinstance(change, dict):
            raise ApiError("Each change must be an object.", 422)
        try:
            old_id = int(change.get("product_id"))
            new_id = int(change["new_product_id"]) if change.get("new_product_id") else old_id
            quantity = parse_quantity(change.get("quantity"), allow_zero=True)
        except (TypeError, ValueError, KeyError) as exc:
            raise ApiError("A suggestion change is invalid.", 422, {"fields": {"changes": str(exc)}}) from exc
        if db.session.get(Product, new_id) is None:
            raise ApiError("That product no longer exists.", 422)
        if old_id != new_id and old_id in by_product:
            db.session.delete(by_product.pop(old_id))
        if quantity <= 0:
            if new_id in by_product:
                db.session.delete(by_product.pop(new_id))
            continue
        if new_id in by_product:
            by_product[new_id].quantity = quantity
        else:
            item = ShoppingListItem(list_id=shopping_list.id, product_id=new_id, quantity=quantity)
            db.session.add(item)
            by_product[new_id] = item
    db.session.commit()
    db.session.refresh(shopping_list)
    return shopping_list


def copy_sample(sample: dict) -> ShoppingList:
    existing = {row.name for row in ShoppingList.query.all()}
    name = sample["name"]
    if name in existing:
        candidate = f"{name} copy"
        number = 2
        while candidate in existing:
            candidate = f"{name} copy {number}"
            number += 1
        name = candidate
    missing = [item["product_id"] for item in sample["items"] if db.session.get(Product, item["product_id"]) is None]
    if missing:
        raise ApiError("This sample list refers to products that are not loaded.", 422, {"product_ids": missing})
    shopping_list = ShoppingList(name=name)
    db.session.add(shopping_list)
    db.session.flush()
    for item in sample["items"]:
        db.session.add(
            ShoppingListItem(
                list_id=shopping_list.id,
                product_id=item["product_id"],
                quantity=Decimal(item["quantity"]),
            )
        )
    db.session.commit()
    return shopping_list
