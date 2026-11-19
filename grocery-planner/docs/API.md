# HTTP API

Base URL when the app is running locally: `http://127.0.0.1:5000`.

All responses are JSON except CSV exports. Errors use:

```json
{"error": "What went wrong", "details": {"fields": {"price": "Amount must be greater than 0."}}}
```

`details` is an object. It may be empty. Status codes: 200, 201, 400, 404, 409, 422.

Money in responses is integer paise plus a `display` string such as `₹1,234.50`. Send money to the API as a rupee string with at most two decimal places (`"40.00"`). The browser does not calculate basket totals.

## Config and catalogue

### `GET /api/config`

Currency symbol, code, thousands separator, decimal places, server date, and `default_month`.

### `GET /api/categories`

`{"categories": [{"id": 1, "name": "Dairy"}]}`

### `POST /api/categories`

`{"name": "Frozen"}` → 201, or 409 if the name exists.

### `GET /api/brands`

`{"brands": ["Amul", "Tata"]}`

### `GET /api/products`

Query: `q`, `category_id`, `brand`, `sort` (`name_asc`, `name_desc`, `price_asc`, `price_desc`, `unit_price_asc`, `unit_price_desc`), `page`, `per_page` (max 300), `in_stock=1`.

Each product includes `cheapest` (pack price, per-unit price, store) or `null` when nothing is in stock.

### `GET /api/products/<id>`

Product fields, `summary`, and `offers[]` for every store. `is_cheapest` is true on the lowest in-stock offer.

### `GET /api/products/<id>/prices`

`dates`, and `series[]` with `values` (major units for the chart), `displays`, and `in_stock`, aligned to `dates`.

### `POST /api/products` and `PUT /api/products/<id>`

```json
{"name": "Taaza Milk", "brand": "Amul", "category_id": 5, "pack_size": "1 L", "unit": "L", "base_unit_qty": "1"}
```

Units: `kg`, `g`, `L`, `ml`, `piece`.

### `DELETE /api/products/<id>`

422 if a price or list line still uses it.

## Stores

### `GET /api/stores`

### `POST /api/stores` and `PUT /api/stores/<id>`

```json
{
  "name": "NearMart",
  "type": "supermarket",
  "area": "Jayanagar",
  "distance_km": "1.20",
  "delivery_fee": "40.00",
  "free_delivery_above": "799.00",
  "rating": "4.2"
}
```

`type` is `supermarket`, `local kirana`, `online`, or `wholesale`. Omit `free_delivery_above` if delivery is never waived. At most 12 stores.

### `DELETE /api/stores/<id>`

422 if prices still reference it.

## Prices

### `GET /api/prices?product_id=&store_id=&limit=`

### `POST /api/prices`

```json
{"product_id": 1, "store_id": 2, "price": "64.00", "date": "2026-11-16", "in_stock": true}
```

The same product, store, and date updates the existing row.

### `PUT /api/prices/<id>` and `DELETE /api/prices/<id>`

### `POST /api/prices/import`

Multipart field `file`, or a raw CSV body. Columns: `product_id,store_id,price,date,in_stock`.

```json
{"imported": 10, "updated": 2, "errors": [{"row": 4, "reason": "price must be greater than 0"}]}
```

200 when at least one row is saved. 422 when every row fails. Row 1 is the header.

## Lists

### `GET /api/lists` and `GET /api/lists/<id>`

### `POST /api/lists` and `PUT /api/lists/<id>`

```json
{"name": "Weekly shop", "items": [{"product_id": 1, "quantity": "2"}]}
```

Quantity is packs, greater than 0, at most 999, two decimal places. PUT replaces the items.

### `DELETE /api/lists/<id>`

### `GET /api/lists/samples`

Names and item counts from `data/sample_lists.csv`.

### `POST /api/lists/samples`

`{"name": "Weekly essentials"}` copies the sample into a new list.

### `POST /api/lists/<id>/estimate`

`{"max_stores": 2}` where `max_stores` is 1, 2, or 3.

Response highlights:

- `strategies.cheapest_single`, `strategies.cheapest_split`, `strategies.nearest`
- each strategy has `total_display`, `delivery_display`, `complete`, `missing`, `lines`, `stores_used`, `savings_display`
- `most_expensive` is the dearest complete single store
- `recommended_key` is the cheapest complete strategy
- `store_estimates` is one total per store
- `items[].choices` is the per-item "buy here" text for the three strategies

Savings are null when the basket is incomplete. Missing items are listed and never dropped.

### `POST /api/lists/<id>/fit`

`{"month": "2026-11", "max_stores": 3}`

Requires a budget. Returns `within_budget`, `message`, and `suggestions[]` with `new_total_display` and `changes`.

### `POST /api/lists/<id>/apply`

`{"changes": [{"product_id": 1, "new_product_id": 9, "quantity": "1.00"}]}`

Quantity `0` removes the line.

## Budgets

### `GET /api/budgets`

### `POST /api/budgets`

409 if that month exists.

```json
{"month": "2026-11", "total": "15000.00", "categories": [{"category_id": 5, "limit": "2500.00"}]}
```

### `PUT /api/budgets/<month>`

Replaces the total and category limits.

### `DELETE /api/budgets/<month>`

### `GET /api/budgets/<month>/summary?as_of=YYYY-MM-DD`

Actual, planned, committed, remaining, percent used, `progress_tone`, projected month-end spend, warnings, category rows, chart values, and expense lines.

Warnings:

- `total_high` / `category_high` when committed is above 80% and at most 100%
- `total_over` / `category_over` when committed is above 100%

Projection follows actual spend only: `actual * days_in_month / days_elapsed`.

### `POST /api/budgets/<month>/expenses`

The server re-estimates. Amounts in the body are ignored.

```json
{"list_id": 1, "strategy": "cheapest_split", "max_stores": 2, "status": "actual"}
```

`strategy` is `cheapest_single`, `cheapest_split`, or `nearest`. `status` is `planned` or `actual`. Incomplete strategies return 422 with `details.missing`. Delivery fees are stored as expense lines without a product.

### `DELETE /api/budgets/<month>/expenses/<id>`

## Insights and export

### `GET /api/insights`

Cheapest store for the Monthly family staples basket, biggest drops in the month of the latest price, savings achieved on recorded actual purchases, and catalogue counts. `drop_chart.values` are major-unit numbers for Chart.js.

### `GET /api/admin/export/<dataset>.csv`

`dataset` is `stores`, `categories`, `products`, or `prices`.
