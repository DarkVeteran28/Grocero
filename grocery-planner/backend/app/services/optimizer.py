"""Basket costs. Combinations stay exact for up to 12 stores and 3 stores per plan."""

from copy import deepcopy
from dataclasses import dataclass, field
from decimal import Decimal
from itertools import combinations

from app.services.units import as_decimal, line_total_paise


def delivery_charge(subtotal_paise: int, delivery_fee: int, free_delivery_above: int | None) -> int:
    """Fee for one store. A zero subtotal means the store was not used."""
    if subtotal_paise <= 0:
        return 0
    if free_delivery_above is not None and subtotal_paise >= int(free_delivery_above):
        return 0
    return int(delivery_fee)


@dataclass
class StoreInfo:
    id: int
    name: str
    distance_km: Decimal
    delivery_fee: int
    free_delivery_above: int | None
    area: str = ""
    type: str = ""


@dataclass
class BasketItem:
    product_id: int
    name: str
    quantity: Decimal
    category_id: int
    quotes: dict = field(default_factory=dict)
    brand: str = ""
    pack_size: str = ""
    unit: str = ""
    base_unit_qty: Decimal = Decimal("1")


def _missing(item: BasketItem) -> dict:
    return {
        "product_id": item.product_id,
        "name": item.name,
        "quantity": format(as_decimal(item.quantity), "f"),
    }


def _line(item: BasketItem, store: StoreInfo | None, unit_price: int | None, available: bool) -> dict:
    quantity = as_decimal(item.quantity)
    line_paise = line_total_paise(unit_price, quantity) if available and unit_price is not None else 0
    return {
        "product_id": item.product_id,
        "name": item.name,
        "brand": item.brand,
        "pack_size": item.pack_size,
        "unit": item.unit,
        "category_id": item.category_id,
        "base_unit_qty": format(as_decimal(item.base_unit_qty), "f"),
        "quantity": format(quantity, "f"),
        "store_id": store.id if store is not None else None,
        "store_name": store.name if store is not None else None,
        "unit_price_paise": int(unit_price) if available else None,
        "line_paise": line_paise,
        "available": available,
    }


def _quote(item: BasketItem, store: StoreInfo):
    quote = item.quotes.get(store.id)
    if not quote or not quote[1]:
        return None
    return int(quote[0])


def estimate_subset(stores: list[StoreInfo], items: list[BasketItem]) -> dict:
    lines = []
    missing = []
    subtotals = {store.id: 0 for store in stores}
    for item in items:
        options = []
        for store in stores:
            price = _quote(item, store)
            if price is None:
                continue
            options.append((price, store.distance_km, store.id, store))
        if not options:
            missing.append(_missing(item))
            lines.append(_line(item, None, None, False))
            continue
        options.sort()
        price, _distance, _store_id, store = options[0]
        subtotals[store.id] += line_total_paise(price, item.quantity)
        lines.append(_line(item, store, price, True))

    stores_used = []
    delivery_total = 0
    distance = Decimal("0")
    for store in stores:
        subtotal = subtotals[store.id]
        if subtotal <= 0:
            continue
        fee = delivery_charge(subtotal, store.delivery_fee, store.free_delivery_above)
        delivery_total += fee
        distance += as_decimal(store.distance_km)
        stores_used.append(
            {
                "id": store.id,
                "name": store.name,
                "area": store.area,
                "type": store.type,
                "distance_km": as_decimal(store.distance_km),
                "subtotal_paise": subtotal,
                "delivery_paise": fee,
            }
        )
    subtotal = sum(subtotals.values())
    return {
        "complete": not missing,
        "store_ids": [store["id"] for store in stores_used],
        "stores_used": stores_used,
        "subtotal_paise": subtotal,
        "delivery_paise": delivery_total,
        "total_paise": subtotal + delivery_total,
        "missing": missing,
        "lines": lines,
        "distance_km": distance,
    }


def _rank(estimate: dict):
    return (
        0 if estimate["complete"] else 1,
        estimate["total_paise"],
        len(estimate["stores_used"]),
        estimate["distance_km"],
        tuple(estimate["store_ids"]),
    )


def _tagged(estimate: dict, key: str, title: str) -> dict:
    copy = deepcopy(estimate)
    copy["key"] = key
    copy["title"] = title
    return copy


def optimize(stores: list[StoreInfo], items: list[BasketItem], max_stores: int = 3) -> dict:
    if not stores:
        raise ValueError("At least one store is required.")
    if max_stores not in (1, 2, 3):
        raise ValueError("max_stores must be 1, 2, or 3.")
    if len(stores) > 12:
        raise ValueError("The split search supports at most 12 stores.")

    singles = [estimate_subset([store], items) for store in stores]
    cheapest_single = _tagged(min(singles, key=_rank), "cheapest_single", "Cheapest single store")

    nearest_store = min(stores, key=lambda store: (as_decimal(store.distance_km), store.id))
    nearest = _tagged(estimate_subset([nearest_store], items), "nearest", "Nearest store")

    split_candidates = []
    limit = min(max_stores, len(stores))
    for size in range(1, limit + 1):
        for subset in combinations(stores, size):
            split_candidates.append(estimate_subset(list(subset), items))
    cheapest_split = _tagged(
        min(split_candidates, key=_rank),
        "cheapest_split",
        f"Cheapest split (up to {max_stores} stores)",
    )

    complete_singles = [estimate for estimate in singles if estimate["complete"]]
    most = None
    if complete_singles:
        most = _tagged(
            max(complete_singles, key=lambda estimate: (estimate["total_paise"], estimate["distance_km"])),
            "most_expensive",
            "Most expensive single store",
        )
        most["savings_paise"] = 0

    strategies = {
        "cheapest_single": cheapest_single,
        "cheapest_split": cheapest_split,
        "nearest": nearest,
    }
    for strategy in strategies.values():
        if most is None or not strategy["complete"]:
            strategy["savings_paise"] = None
        else:
            strategy["savings_paise"] = most["total_paise"] - strategy["total_paise"]

    recommended = None
    complete = [strategy for strategy in strategies.values() if strategy["complete"]]
    if complete:
        priority = {"cheapest_single": 0, "cheapest_split": 1, "nearest": 2}
        recommended = min(
            complete,
            key=lambda strategy: (
                strategy["total_paise"],
                len(strategy["stores_used"]),
                priority[strategy["key"]],
            ),
        )["key"]

    return {
        "max_stores": max_stores,
        "strategies": strategies,
        "most_expensive": most,
        "store_estimates": [_tagged(estimate, "store", "Single store") for estimate in singles],
        "recommended_key": recommended,
    }
