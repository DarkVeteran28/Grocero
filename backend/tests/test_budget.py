from datetime import date
from decimal import Decimal

from app.services.budget import build_warnings, project_month_end, suggest_adjustments


def test_projection_pace():
    assert project_month_end(300000, "2026-11", date(2026, 11, 10)) == 900000
    assert project_month_end(300000, "2026-11", date(2026, 10, 31)) == 0
    assert project_month_end(300000, "2026-11", date(2026, 11, 30)) == 300000


def test_warning_thresholds():
    categories = [{"category_id": 1, "name": "Dairy", "limit_paise": 20000, "committed_paise": 16000}]
    assert build_warnings(100000, 80000, categories) == []
    high = build_warnings(100000, 81000, categories)
    assert [row["code"] for row in high] == ["total_high"]
    exact = build_warnings(100000, 100000, [])
    assert exact[0]["code"] == "total_high"
    over = build_warnings(100000, 100001, [])
    assert over[0]["code"] == "total_over"
    dairy = [{"category_id": 1, "name": "Dairy", "limit_paise": 20000, "committed_paise": 21000}]
    assert build_warnings(None, 0, dairy)[0]["code"] == "category_over"


def test_fit_suggestions_are_priced_by_the_server():
    lines = [
        {
            "product_id": 1,
            "name": "Milk",
            "brand": "Amul",
            "pack_size": "1 L",
            "category_id": 1,
            "quantity": Decimal("2"),
            "base_unit_qty": Decimal("1"),
            "unit": "L",
            "line_paise": 12000,
            "unit_price_paise": 6000,
            "per_unit_paise": 6000,
            "available": True,
        }
    ]
    alternatives = [
        {
            "product_id": 9,
            "name": "Toned Milk",
            "brand": "Nandini",
            "pack_size": "1 L",
            "category_id": 1,
            "base_unit_qty": Decimal("1"),
            "unit": "L",
            "pack_price_paise": 4000,
            "per_unit_paise": 4000,
            "store_name": "FarShop",
        }
    ]
    advice = suggest_adjustments(
        lines=lines,
        alternatives=alternatives,
        remaining_paise=10000,
        basket_total_paise=12000,
        complete=True,
    )
    assert advice["within_budget"] is False
    assert advice["over_by_paise"] == 2000
    kinds = {row["type"]: row for row in advice["suggestions"]}
    assert kinds["swap"]["new_total_paise"] == 8000
    assert kinds["swap"]["within_budget"] is True
    assert kinds["reduce"]["new_total_paise"] == 6000
    assert kinds["remove"]["new_total_paise"] == 0
