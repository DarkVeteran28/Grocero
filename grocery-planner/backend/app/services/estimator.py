"""Turn a saved list into a fully priced plan."""

from decimal import Decimal

from app.models import Product, ShoppingList, Store
from app.services.optimizer import BasketItem, StoreInfo, optimize
from app.services.pricing import latest_by_product
from app.services.units import as_decimal, per_unit_paise, unit_suffix
from app.utils.errors import ApiError
from app.utils.money import format_money


def _stores() -> list[StoreInfo]:
    rows = Store.query.order_by(Store.id).all()
    return [
        StoreInfo(
            id=row.id,
            name=row.name,
            distance_km=as_decimal(row.distance_km),
            delivery_fee=int(row.delivery_fee),
            free_delivery_above=None if row.free_delivery_above is None else int(row.free_delivery_above),
            area=row.area,
            type=row.type,
        )
        for row in rows
    ]


def _items(shopping_list: ShoppingList) -> list[BasketItem]:
    product_ids = [item.product_id for item in shopping_list.items]
    quotes = {}
    for product_id, rows in latest_by_product(product_ids).items():
        quotes[product_id] = {row.store_id: (int(row.price), bool(row.in_stock)) for row in rows}
    basket = []
    for item in shopping_list.items:
        product = item.product
        basket.append(
            BasketItem(
                product_id=item.product_id,
                name=product.name,
                quantity=as_decimal(item.quantity),
                category_id=product.category_id,
                quotes=quotes.get(item.product_id, {}),
                brand=product.brand,
                pack_size=product.pack_size,
                unit=product.unit,
                base_unit_qty=as_decimal(product.base_unit_qty),
            )
        )
    return basket


def _present_line(line: dict) -> dict:
    presented = dict(line)
    presented["quantity"] = format(Decimal(str(line["quantity"])), "f")
    if line["available"] and line["unit_price_paise"] is not None:
        per_unit = per_unit_paise(line["unit_price_paise"], line["base_unit_qty"])
        presented["per_unit_paise"] = per_unit
        suffix = unit_suffix(line["unit"])
        presented["per_unit_display"] = f"{format_money(per_unit)}/{suffix}"
        presented["unit_price_display"] = format_money(line["unit_price_paise"])
        presented["line_display"] = format_money(line["line_paise"])
    else:
        presented["per_unit_paise"] = None
        presented["per_unit_display"] = None
        presented["unit_price_display"] = None
        presented["line_display"] = None
    return presented


def _present_strategy(strategy: dict) -> dict:
    distance = as_decimal(strategy["distance_km"])
    savings = strategy.get("savings_paise")
    stores_used = []
    for store in strategy["stores_used"]:
        stores_used.append(
            {
                "id": store["id"],
                "name": store["name"],
                "area": store.get("area", ""),
                "type": store.get("type", ""),
                "distance_km": format(as_decimal(store["distance_km"]), "f"),
                "distance_display": f"{format(as_decimal(store['distance_km']), 'f')} km",
                "subtotal_paise": store["subtotal_paise"],
                "subtotal_display": format_money(store["subtotal_paise"]),
                "delivery_paise": store["delivery_paise"],
                "delivery_display": format_money(store["delivery_paise"]),
            }
        )
    return {
        "key": strategy["key"],
        "title": strategy["title"],
        "complete": strategy["complete"],
        "store_ids": list(strategy["store_ids"]),
        "stores_used": stores_used,
        "subtotal_paise": strategy["subtotal_paise"],
        "subtotal_display": format_money(strategy["subtotal_paise"]),
        "delivery_paise": strategy["delivery_paise"],
        "delivery_display": format_money(strategy["delivery_paise"]),
        "total_paise": strategy["total_paise"],
        "total_display": format_money(strategy["total_paise"]),
        "savings_paise": savings,
        "savings_display": format_money(savings) if savings is not None else None,
        "distance_km": format(distance, "f"),
        "distance_display": f"{format(distance, 'f')} km",
        "missing": strategy["missing"],
        "lines": [_present_line(line) for line in strategy["lines"]],
    }


def _matrix(strategies: dict) -> list[dict]:
    order = ["cheapest_single", "cheapest_split", "nearest"]
    base_lines = strategies["cheapest_single"]["lines"]
    rows = []
    for index, line in enumerate(base_lines):
        choices = {}
        for key in order:
            choice = strategies[key]["lines"][index]
            choices[key] = {
                "store_name": choice["store_name"],
                "available": choice["available"],
                "line_display": choice["line_display"],
                "unit_price_display": choice["unit_price_display"],
            }
        rows.append(
            {
                "product_id": line["product_id"],
                "name": line["name"],
                "brand": line["brand"],
                "pack_size": line["pack_size"],
                "quantity": line["quantity"],
                "choices": choices,
            }
        )
    return rows


def estimate_list(shopping_list: ShoppingList, max_stores: int) -> dict:
    if not shopping_list.items:
        raise ApiError("Add a product before estimating this list.", 422, {"fields": {"items": "The list is empty."}})
    stores = _stores()
    if not stores:
        raise ApiError("Add a store before estimating a list.", 422)
    plan = optimize(stores, _items(shopping_list), max_stores)
    strategies = {key: _present_strategy(value) for key, value in plan["strategies"].items()}
    most = _present_strategy(plan["most_expensive"]) if plan["most_expensive"] else None
    return {
        "list_id": shopping_list.id,
        "list_name": shopping_list.name,
        "max_stores": max_stores,
        "recommended_key": plan["recommended_key"],
        "strategies": strategies,
        "most_expensive": most,
        "store_estimates": [_present_strategy(row) for row in plan["store_estimates"]],
        "items": _matrix(strategies),
    }


def basket_from_products(pairs: list[tuple[Product, Decimal]]) -> list[BasketItem]:
    product_ids = [product.id for product, _quantity in pairs]
    quotes = {}
    for product_id, rows in latest_by_product(product_ids).items():
        quotes[product_id] = {row.store_id: (int(row.price), bool(row.in_stock)) for row in rows}
    return [
        BasketItem(
            product_id=product.id,
            name=product.name,
            quantity=quantity,
            category_id=product.category_id,
            quotes=quotes.get(product.id, {}),
            brand=product.brand,
            pack_size=product.pack_size,
            unit=product.unit,
            base_unit_qty=as_decimal(product.base_unit_qty),
        )
        for product, quantity in pairs
    ]
