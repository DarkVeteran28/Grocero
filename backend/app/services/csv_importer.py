"""CSV load, price import, and export."""

import csv
import io
from datetime import datetime
from decimal import Decimal

from app.extensions import db
from app.models import Category, Price, Product, ShoppingList, ShoppingListItem, Store
from app.utils.money import to_paise


def _rupees(paise: int) -> str:
    return f"{Decimal(int(paise)) / Decimal(100):.2f}"
from app.utils.validation import parse_bool, parse_date, parse_int

PRICE_COLUMNS = ["product_id", "store_id", "price", "date", "in_stock"]


def _reader(text: str):
    if text.startswith("\ufeff"):
        text = text[1:]
    return csv.DictReader(io.StringIO(text))


def parse_price_csv(text: str, product_ids: set[int], store_ids: set[int]):
    reader = _reader(text)
    if not reader.fieldnames:
        return [], [{"row": 1, "reason": "CSV header is missing."}]
    fields = [name.strip() for name in reader.fieldnames if name]
    missing = [column for column in PRICE_COLUMNS if column not in fields]
    if missing:
        return [], [{"row": 1, "reason": "Missing columns: " + ", ".join(missing)}]
    rows = []
    errors = []
    for index, raw in enumerate(reader, start=2):
        if raw is None or all(not (value or "").strip() for value in raw.values()):
            continue
        reasons = []
        try:
            product_id = parse_int(raw.get("product_id"), "product_id")
            if product_id not in product_ids:
                reasons.append("product_id not found")
        except ValueError:
            product_id = None
            reasons.append("product_id is invalid")
        try:
            store_id = parse_int(raw.get("store_id"), "store_id")
            if store_id not in store_ids:
                reasons.append("store_id not found")
        except ValueError:
            store_id = None
            reasons.append("store_id is invalid")
        try:
            price = to_paise(raw.get("price"))
        except ValueError as exc:
            price = None
            reasons.append(str(exc).rstrip("."))
        try:
            price_date = parse_date((raw.get("date") or "").strip())
        except ValueError:
            price_date = None
            reasons.append("date must be YYYY-MM-DD")
        try:
            in_stock = parse_bool(raw.get("in_stock"))
        except ValueError:
            in_stock = None
            reasons.append("in_stock must be true or false")
        if reasons:
            errors.append({"row": index, "reason": "; ".join(reasons)})
            continue
        rows.append(
            {
                "product_id": product_id,
                "store_id": store_id,
                "price": price,
                "date": price_date,
                "in_stock": in_stock,
            }
        )
    return rows, errors


def apply_price_rows(rows: list[dict]) -> tuple[int, int]:
    if not rows:
        return 0, 0
    product_ids = {row["product_id"] for row in rows}
    existing = {
        (row.product_id, row.store_id, row.date): row
        for row in Price.query.filter(Price.product_id.in_(product_ids)).all()
    }
    imported = 0
    updated = 0
    for row in rows:
        key = (row["product_id"], row["store_id"], row["date"])
        current = existing.get(key)
        if current is None:
            current = Price(
                product_id=row["product_id"],
                store_id=row["store_id"],
                price=row["price"],
                date=row["date"],
                in_stock=row["in_stock"],
            )
            db.session.add(current)
            existing[key] = current
            imported += 1
        else:
            current.price = row["price"]
            current.in_stock = row["in_stock"]
            updated += 1
    db.session.commit()
    return imported, updated


def _require(path):
    if not path.is_file():
        raise FileNotFoundError(f"Missing data file: {path}")
    return path.read_text(encoding="utf-8-sig")


def load_csvs(data_dir) -> dict:
    """Replace catalog tables with the CSV dataset and create the sample lists."""
    data_dir = data_dir if hasattr(data_dir, "joinpath") else __import__("pathlib").Path(data_dir)
    categories = list(csv.DictReader(io.StringIO(_require(data_dir / "categories.csv"))))
    stores = list(csv.DictReader(io.StringIO(_require(data_dir / "stores.csv"))))
    products = list(csv.DictReader(io.StringIO(_require(data_dir / "products.csv"))))
    prices = list(csv.DictReader(io.StringIO(_require(data_dir / "prices.csv"))))
    samples = list(csv.DictReader(io.StringIO(_require(data_dir / "sample_lists.csv"))))

    for row in categories:
        db.session.add(Category(id=int(row["category_id"]), name=row["name"].strip()))
    db.session.flush()
    for row in stores:
        free = (row.get("free_delivery_above") or "").strip()
        db.session.add(
            Store(
                id=int(row["store_id"]),
                name=row["name"].strip(),
                type=row["type"].strip(),
                area=row["area"].strip(),
                distance_km=Decimal(row["distance_km"]),
                delivery_fee=to_paise(row["delivery_fee"], allow_zero=True),
                free_delivery_above=None if free == "" else to_paise(free),
                rating=Decimal(row["rating"]),
            )
        )
    db.session.flush()
    for row in products:
        db.session.add(
            Product(
                id=int(row["product_id"]),
                name=row["name"].strip(),
                brand=row["brand"].strip(),
                category_id=int(row["category_id"]),
                pack_size=row["pack_size"].strip(),
                unit=row["unit"].strip(),
                base_unit_qty=Decimal(row["base_unit_qty"]),
            )
        )
    db.session.flush()
    db.session.execute(
        Price.__table__.insert(),
        [
            {
                "product_id": int(row["product_id"]),
                "store_id": int(row["store_id"]),
                "price": to_paise(row["price"]),
                "date": datetime.strptime(row["date"], "%Y-%m-%d").date(),
                "in_stock": str(row["in_stock"]).strip().lower() in {"true", "1", "yes", "y"},
            }
            for row in prices
        ],
    )
    grouped = {}
    for row in samples:
        grouped.setdefault(row["list_name"].strip(), []).append(row)
    for name, items in grouped.items():
        shopping_list = ShoppingList(name=name)
        db.session.add(shopping_list)
        db.session.flush()
        for item in items:
            db.session.add(
                ShoppingListItem(
                    list_id=shopping_list.id,
                    product_id=int(item["product_id"]),
                    quantity=Decimal(item["quantity"]),
                )
            )
    db.session.commit()
    return {
        "categories": len(categories),
        "stores": len(stores),
        "products": len(products),
        "prices": len(prices),
        "lists": len(grouped),
    }


def read_sample_lists(data_dir):
    path = data_dir / "sample_lists.csv"
    if not path.is_file():
        return []
    rows = list(csv.DictReader(io.StringIO(path.read_text(encoding="utf-8-sig"))))
    grouped = {}
    for row in rows:
        grouped.setdefault(row["list_name"].strip(), []).append(
            {
                "product_id": int(row["product_id"]),
                "quantity": str(Decimal(row["quantity"])),
                "product_name": (row.get("product_name") or "").strip(),
                "pack_size": (row.get("pack_size") or "").strip(),
            }
        )
    return [{"name": name, "items": items, "item_count": len(items)} for name, items in grouped.items()]


def export_csv(dataset: str) -> tuple[str, str]:
    buffer = io.StringIO()
    writer = csv.writer(buffer)
    if dataset == "categories":
        writer.writerow(["category_id", "name"])
        for row in Category.query.order_by(Category.id):
            writer.writerow([row.id, row.name])
    elif dataset == "stores":
        writer.writerow(
            ["store_id", "name", "type", "area", "distance_km", "delivery_fee", "free_delivery_above", "rating"]
        )
        for row in Store.query.order_by(Store.id):
            writer.writerow(
                [
                    row.id,
                    row.name,
                    row.type,
                    row.area,
                    format(row.distance_km, "f"),
                    _rupees(row.delivery_fee),
                    "" if row.free_delivery_above is None else _rupees(row.free_delivery_above),
                    format(row.rating, "f"),
                ]
            )
    elif dataset == "products":
        writer.writerow(["product_id", "name", "brand", "category_id", "pack_size", "unit", "base_unit_qty"])
        for row in Product.query.order_by(Product.id):
            writer.writerow(
                [row.id, row.name, row.brand, row.category_id, row.pack_size, row.unit, format(row.base_unit_qty, "f")]
            )
    elif dataset == "prices":
        writer.writerow(PRICE_COLUMNS)
        for row in Price.query.order_by(Price.product_id, Price.store_id, Price.date):
            writer.writerow(
                [
                    row.product_id,
                    row.store_id,
                    _rupees(row.price),
                    row.date.isoformat(),
                    "true" if row.in_stock else "false",
                ]
            )
    else:
        raise KeyError(dataset)
    return buffer.getvalue(), f"{dataset}.csv"
