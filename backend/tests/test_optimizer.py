from decimal import Decimal

from app.services.optimizer import BasketItem, StoreInfo, delivery_charge, estimate_subset, optimize


def _stores():
    return [
        StoreInfo(1, "NearMart", Decimal("1.2"), 4000, 20000),
        StoreInfo(2, "BudgetBazaar", Decimal("4.5"), 2000, 15000),
        StoreInfo(3, "FarShop", Decimal("8"), 0, None),
    ]


def _items():
    return [
        BasketItem(1, "Milk", Decimal("1"), 1, {1: (8000, True), 2: (6000, True), 3: (9000, True)}),
        BasketItem(2, "Rice", Decimal("1"), 2, {1: (5000, True), 2: (7000, True), 3: (4000, True)}),
    ]


def test_delivery_threshold_boundaries():
    assert delivery_charge(0, 4000, 20000) == 0
    assert delivery_charge(19999, 4000, 20000) == 4000
    assert delivery_charge(20000, 4000, 20000) == 0
    assert delivery_charge(5000, 1500, None) == 1500


def test_split_matches_hand_worked_example():
    plan = optimize(_stores(), _items(), max_stores=2)
    assert plan["strategies"]["cheapest_single"]["total_paise"] == 13000
    assert plan["strategies"]["cheapest_single"]["store_ids"] == [3]
    assert plan["strategies"]["cheapest_single"]["savings_paise"] == 4000
    assert plan["strategies"]["nearest"]["store_ids"] == [1]
    assert plan["strategies"]["nearest"]["total_paise"] == 17000
    assert plan["strategies"]["nearest"]["savings_paise"] == 0
    split = plan["strategies"]["cheapest_split"]
    assert split["total_paise"] == 12000
    assert split["store_ids"] == [2, 3]
    assert split["savings_paise"] == 5000
    assert split["delivery_paise"] == 2000
    bought = {line["product_id"]: line["store_id"] for line in split["lines"]}
    assert bought == {1: 2, 2: 3}
    assert plan["most_expensive"]["total_paise"] == 17000
    assert plan["recommended_key"] == "cheapest_split"


def test_missing_items_are_reported():
    items = _items() + [BasketItem(3, "Soap", Decimal("1"), 1, {1: (1000, True)})]
    estimate = estimate_subset(_stores()[1:], items)
    assert estimate["complete"] is False
    assert estimate["missing"][0]["product_id"] == 3
    assert any(line["product_id"] == 3 and line["available"] is False for line in estimate["lines"])
    assert len(estimate["lines"]) == 3
