"""Seed a temporary database and request every page plus the main API routes."""

import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app import create_app
from app.config import DATA_DIR, Config
from app.extensions import db
from app.services.csv_importer import load_csvs

PAGES = [
    "/",
    "/index.html",
    "/compare.html",
    "/product.html",
    "/lists.html",
    "/budget.html",
    "/insights.html",
    "/admin.html",
    "/css/base.css",
    "/css/layout.css",
    "/css/components.css",
    "/js/api.js",
    "/js/utils.js",
    "/js/components/navbar.js",
    "/vendor/chart.min.js",
    "/assets/favicon.svg",
]

APIS = [
    "/api/config",
    "/api/categories",
    "/api/brands",
    "/api/products?q=milk",
    "/api/stores",
    "/api/lists",
    "/api/lists/samples",
    "/api/budgets",
    "/api/insights",
]


class SmokeConfig(Config):
    TESTING = True


def main():
    with tempfile.TemporaryDirectory() as tmp:
        SmokeConfig.SQLALCHEMY_DATABASE_URI = "sqlite:///" + str(Path(tmp) / "smoke.db")
        app = create_app(SmokeConfig)
        with app.app_context():
            db.drop_all()
            db.create_all()
            load_csvs(DATA_DIR)
        client = app.test_client()
        failures = []
        for path in PAGES + APIS:
            response = client.get(path)
            if response.status_code != 200:
                failures.append(f"{path} -> {response.status_code}")
        products = client.get("/api/products?per_page=1").get_json()
        if products["products"]:
            product_id = products["products"][0]["id"]
            for path in (f"/api/products/{product_id}", f"/api/products/{product_id}/prices"):
                response = client.get(path)
                if response.status_code != 200:
                    failures.append(f"{path} -> {response.status_code}")
        lists = client.get("/api/lists").get_json()["lists"]
        if lists:
            response = client.post(f"/api/lists/{lists[0]['id']}/estimate", json={"max_stores": 2})
            if response.status_code != 200:
                failures.append(f"estimate -> {response.status_code} {response.get_data(as_text=True)[:300]}")
        if failures:
            print("Smoke test failed:")
            for failure in failures:
                print(" ", failure)
            return 1
        print(f"Smoke test passed ({len(PAGES) + len(APIS)} routes).")
        return 0


if __name__ == "__main__":
    sys.exit(main())
