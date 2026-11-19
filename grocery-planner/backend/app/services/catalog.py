"""Product search and the price-history payload consumed by the chart."""

from decimal import Decimal

from app.models import Category, Price, Product, Store
from app.services.pricing import latest_by_product
from app.services.units import as_decimal, per_unit_paise, unit_suffix
from app.utils.money import chart_amount, format_money


def list_categories():
    return [row.to_dict() for row in Category.query.order_by(Category.name).all()]


def list_brands():
    rows = Product.query.with_entities(Product.brand).distinct().order_by(Product.brand).all()
    return [row[0] for row in rows]


def _offer(product: Product, row: Price, store: Store) -> dict:
    per_unit = per_unit_paise(row.price, product.base_unit_qty)
    suffix = unit_suffix(product.unit)
    return {
        "price_id": row.id,
        "store_id": store.id,
        "store_name": store.name,
        "store_type": store.type,
        "area": store.area,
        "distance_km": format(store.distance_km, "f"),
        "distance_display": f"{format(store.distance_km, 'f')} km",
        "price_paise": int(row.price),
        "price_display": format_money(row.price),
        "per_unit_paise": per_unit,
        "per_unit_display": f"{format_money(per_unit)}/{suffix}",
        "in_stock": bool(row.in_stock),
        "date": row.date.isoformat(),
        "is_cheapest": False,
    }


def offers_for(product: Product, rows, stores_by_id) -> list[dict]:
    offers = []
    for row in rows:
        store = stores_by_id.get(row.store_id)
        if store is None:
            continue
        offers.append(_offer(product, row, store))
    in_stock = [offer for offer in offers if offer["in_stock"]]
    if in_stock:
        cheapest = min(in_stock, key=lambda offer: (offer["price_paise"], Decimal(offer["distance_km"]), offer["store_id"]))
        for offer in offers:
            offer["is_cheapest"] = offer["store_id"] == cheapest["store_id"] and offer["in_stock"]
    offers.sort(key=lambda offer: (not offer["in_stock"], offer["price_paise"], offer["store_name"]))
    return offers


def _cheapest(offers: list[dict]):
    for offer in offers:
        if offer["is_cheapest"]:
            return offer
    return None


def search_products(*, q="", category_id=None, brand="", sort="name_asc", page=1, per_page=30, in_stock_only=False):
    query = Product.query.join(Category)
    if q:
        like = f"%{q.strip()}%"
        query = query.filter((Product.name.ilike(like)) | (Product.brand.ilike(like)))
    if category_id:
        query = query.filter(Product.category_id == category_id)
    if brand:
        query = query.filter(Product.brand == brand)
    products = query.order_by(Product.name, Product.id).all()
    stores = {store.id: store for store in Store.query.all()}
    latest = latest_by_product([product.id for product in products])
    rows = []
    for product in products:
        offers = offers_for(product, latest.get(product.id, []), stores)
        cheapest = _cheapest(offers)
        if in_stock_only and cheapest is None:
            continue
        payload = product.to_dict()
        payload["offers_count"] = len(offers)
        payload["in_stock_count"] = sum(1 for offer in offers if offer["in_stock"])
        payload["cheapest"] = cheapest
        payload["all_out_of_stock"] = cheapest is None
        rows.append(payload)

    def price_key(row, field):
        cheapest = row["cheapest"]
        if cheapest is None:
            return (1, 0, row["name"].lower(), row["id"])
        return (0, cheapest[field], row["name"].lower(), row["id"])

    if sort == "price_asc":
        rows.sort(key=lambda row: price_key(row, "price_paise"))
    elif sort == "price_desc":
        rows.sort(key=lambda row: (row["cheapest"] is None, -(row["cheapest"]["price_paise"] if row["cheapest"] else 0), row["name"].lower()))
    elif sort == "unit_price_asc":
        rows.sort(key=lambda row: price_key(row, "per_unit_paise"))
    elif sort == "unit_price_desc":
        rows.sort(key=lambda row: (row["cheapest"] is None, -(row["cheapest"]["per_unit_paise"] if row["cheapest"] else 0), row["name"].lower()))
    elif sort == "name_desc":
        rows.sort(key=lambda row: row["name"].lower(), reverse=True)
    else:
        rows.sort(key=lambda row: (row["name"].lower(), row["id"]))

    total = len(rows)
    pages = max(1, (total + per_page - 1) // per_page)
    page = min(page, pages)
    start = (page - 1) * per_page
    return {
        "products": rows[start : start + per_page],
        "page": page,
        "per_page": per_page,
        "total": total,
        "pages": pages,
    }


def product_detail(product: Product) -> dict:
    stores = {store.id: store for store in Store.query.all()}
    rows = latest_by_product([product.id]).get(product.id, [])
    offers = offers_for(product, rows, stores)
    cheapest = _cheapest(offers)
    payload = product.to_dict()
    payload["offers"] = offers
    payload["cheapest"] = cheapest
    if cheapest:
        payload["summary"] = (
            f"Lowest current in-stock price is {cheapest['price_display']} at {cheapest['store_name']} "
            f"({cheapest['per_unit_display']})."
        )
    elif offers:
        payload["summary"] = "Every store that carries this product is currently out of stock."
    else:
        payload["summary"] = "No prices have been recorded for this product."
    return payload


def price_history(product: Product) -> dict:
    rows = Price.query.filter_by(product_id=product.id).order_by(Price.date, Price.store_id).all()
    stores = {store.id: store for store in Store.query.all()}
    dates = []
    seen = set()
    by_store = {}
    for row in rows:
        iso = row.date.isoformat()
        if iso not in seen:
            seen.add(iso)
            dates.append(iso)
        by_store.setdefault(row.store_id, {})[iso] = row
    series = []
    for store_id, points in by_store.items():
        store = stores.get(store_id)
        values = []
        displays = []
        stock = []
        for iso in dates:
            row = points.get(iso)
            if row is None:
                values.append(None)
                displays.append(None)
                stock.append(None)
            else:
                values.append(chart_amount(row.price))
                displays.append(format_money(row.price))
                stock.append(bool(row.in_stock))
        series.append(
            {
                "store_id": store_id,
                "store_name": store.name if store else f"Store {store_id}",
                "values": values,
                "displays": displays,
                "in_stock": stock,
            }
        )
    series.sort(key=lambda item: item["store_name"])
    return {
        "product_id": product.id,
        "name": product.name,
        "dates": dates,
        "series": series,
    }
