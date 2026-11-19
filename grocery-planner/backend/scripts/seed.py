"""Load the generated CSVs into the SQLite database. This replaces existing rows."""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app import create_app
from app.config import DATA_DIR
from app.extensions import db
from app.services.csv_importer import load_csvs


def main():
    app = create_app()
    with app.app_context():
        db.drop_all()
        db.create_all()
        counts = load_csvs(DATA_DIR)
    print(
        "Seeded {stores} stores, {categories} categories, {products} products, "
        "{prices} prices, and {lists} sample lists.".format(**counts)
    )
    print("Database:", app.config["SQLALCHEMY_DATABASE_URI"])


if __name__ == "__main__":
    main()
