def test_config_and_catalog(client):
    config = client.get("/api/config")
    assert config.status_code == 200
    assert config.get_json()["currency_symbol"] == "₹"
    assert config.get_json()["decimal_places"] == 2
    products = client.get("/api/products?sort=price_asc").get_json()
    assert products["total"] == 2
    detail = client.get("/api/products/1")
    assert detail.status_code == 200
    body = detail.get_json()
    assert body["cheapest"]["store_name"] == "BudgetBazaar"
    assert body["cheapest"]["price_paise"] == 6000
    assert body["cheapest"]["per_unit_display"].endswith("/L")
    history = client.get("/api/products/1/prices").get_json()
    assert history["dates"] == ["2026-11-02", "2026-11-16"]
    missing = client.get("/api/products/99")
    assert missing.status_code == 404
    assert "not found" in missing.get_json()["error"].lower()


def test_estimate_matches_hand_worked_totals(client):
    created = client.post(
        "/api/lists",
        json={
            "name": "Test basket",
            "items": [{"product_id": 1, "quantity": "1"}, {"product_id": 2, "quantity": "1"}],
        },
    )
    assert created.status_code == 201
    list_id = created.get_json()["id"]
    estimate = client.post(f"/api/lists/{list_id}/estimate", json={"max_stores": 2})
    assert estimate.status_code == 200
    body = estimate.get_json()
    assert body["strategies"]["cheapest_split"]["total_paise"] == 12000
    assert body["strategies"]["cheapest_single"]["total_paise"] == 13000
    assert body["strategies"]["nearest"]["total_paise"] == 17000
    assert body["items"][0]["choices"]["cheapest_split"]["store_name"] == "BudgetBazaar"
    bad = client.post("/api/lists", json={"name": "Empty qty", "items": [{"product_id": 1, "quantity": "0"}]})
    assert bad.status_code == 422
    assert "error" in bad.get_json()


def test_budget_summary_warnings_and_import(client):
    created = client.post(
        "/api/budgets",
        json={"month": "2026-11", "total": "100.00", "categories": [{"category_id": 1, "limit": "50.00"}]},
    )
    assert created.status_code == 201
    summary = created.get_json()
    assert summary["budget_set"] is True
    assert summary["total_paise"] == 10000
    again = client.post("/api/budgets", json={"month": "2026-11", "total": "10.00"})
    assert again.status_code == 409
    shopping = client.post(
        "/api/lists",
        json={"name": "Shop", "items": [{"product_id": 1, "quantity": "1"}, {"product_id": 2, "quantity": "1"}]},
    ).get_json()
    recorded = client.post(
        "/api/budgets/2026-11/expenses",
        json={"list_id": shopping["id"], "strategy": "cheapest_single", "max_stores": 1, "status": "actual"},
    )
    assert recorded.status_code == 201
    assert recorded.get_json()["total_paise"] == 13000
    summary = client.get("/api/budgets/2026-11/summary?as_of=2026-11-16").get_json()
    assert summary["actual_paise"] == 13000
    assert summary["remaining_paise"] == -3000
    assert "total_over" in {row["code"] for row in summary["warnings"]}
    assert "category_over" in {row["code"] for row in summary["warnings"]}
    upload = client.post(
        "/api/prices/import",
        data={
            "file": (
                __import__("io").BytesIO(
                    b"product_id,store_id,price,date,in_stock\n1,1,70.00,2026-11-16,true\n1,9,5,2026-11-16,true\n"
                ),
                "prices.csv",
            )
        },
    )
    body = upload.get_json()
    assert upload.status_code == 200
    assert body["updated"] == 1
    assert body["errors"][0]["row"] == 3
    bad_file = client.post(
        "/api/prices/import",
        data={"file": (__import__("io").BytesIO(b"product_id,store_id,price,date,in_stock\n9,9,-1,bad,maybe\n"), "bad.csv")},
    )
    assert bad_file.status_code == 422
    assert bad_file.get_json()["details"]["errors"]


def test_html_is_served_beside_the_api(client):
    page = client.get("/compare.html")
    assert page.status_code == 200
    assert b"Compare" in page.data
    assert client.get("/api/stores").status_code == 200
