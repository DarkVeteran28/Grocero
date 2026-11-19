# Smart Grocery Price Comparison and Budget Planner

## Goal

Help someone compare grocery prices across nearby stores, estimate a shopping list under different buying strategies, and track that spend against a monthly budget. The backend owns every price, unit, delivery, and budget calculation. The frontend only collects input and renders API results.

## Stack

- Python 3.10+, Flask, Flask-SQLAlchemy, SQLite, Flask-CORS
- Static HTML, CSS, and vanilla ES modules
- Chart.js 4.4.6 served from `frontend/vendor/chart.min.js`
- pytest for unit and API tests
- Money is integer paise (1 rupee = 100 paise). `Decimal` is used while multiplying quantities. Floats are not used for money.

## Runtime

From `grocery-planner/backend`:

```
pip install -r requirements.txt
python scripts/seed.py
python run.py
```

Open `http://127.0.0.1:5000`. Flask serves `frontend/` at `/` and the JSON API at `/api`. The browser calls relative `/api/...` URLs, so the UI and API share one origin.

`GET /api/config` exposes the currency symbol (default ₹), thousands separator, and 2 decimal places. Storage stays in paise even if the symbol changes in `backend/app/config.py`.

## Data

`data/generate_data.py` builds deterministic CSVs with random seed 42. The price calendar ends on Monday 16 November 2026 and contains 26 weekly observations. `backend/scripts/seed.py` wipes the SQLite file and loads those CSVs. This is sample data, not a live retailer feed. Formats are documented in `data/DATA_README.md`.

Generated shape:

- 10 stores (supermarket, local kirana, online, wholesale)
- 12 categories
- about 200 products, several pack sizes per family
- each product priced at 4–8 stores
- three sample shopping lists

Larger packs are generated so the per-unit price is strictly lower than the smaller pack of the same product, at the same store, on the same day.

## Schema

SQLite tables, created by SQLAlchemy:

- `stores` — name, type, area, distance, delivery fee, free-delivery threshold, rating
- `categories` — name
- `products` — brand, name, category, pack size, unit, `base_unit_qty`
- `prices` — product, store, price paise, date, in_stock. Unique on `(product_id, store_id, date)`. Current price is the latest date.
- `shopping_lists` and `shopping_list_items` — quantity of packs, greater than 0
- `budgets` — one row per `YYYY-MM`, total paise
- `category_budgets` — optional limit per category
- `expenses` — dated line (product or delivery), store, amount paise, category, status `planned` or `actual`

Foreign keys are enforced. Checks reject a price or quantity that is not positive. Indexes cover `prices.product_id`, `prices.store_id`, and `prices.date`.

The diagram is in `docs/ER.md`.

## Services

Routes parse HTTP and call services. They do not price a basket themselves.

| Module | Responsibility |
| --- | --- |
| `services/units.py` | Per-kg, per-L, and per-piece normalisation from `base_unit_qty` |
| `services/optimizer.py` | Single-store totals, delivery threshold, split search, nearest store |
| `services/estimator.py` | Load a list, attach current quotes, return a JSON-safe plan |
| `services/budget.py` | Month summary, projection, warnings, fit-to-budget suggestions |
| `services/pricing.py` | Current price lookup and price history |
| `services/catalog.py` | Search, product detail, create/update validation assembly |
| `services/csv_importer.py` | Full seed load, price CSV validation, export |
| `services/insights.py` | Reference-basket winner, monthly drops, savings achieved |

### Units

`base_unit_qty` is the pack expressed in kilograms, litres, or pieces. Per-unit paise is `price_paise / base_unit_qty`, rounded half-up to a paisa. Grams and millilitres are already converted in the stored quantity (500 g → 0.5 kg, 500 ml → 0.5 L).

### Delivery

If the store subtotal is 0, the delivery fee is 0 because nothing is purchased there. If the subtotal is at least `free_delivery_above`, the fee is 0. Otherwise the store's delivery fee is added. A missing threshold means the fee always applies.

### Strategies

For a list and `max_stores` of 1, 2, or 3:

1. **Cheapest single store.** Price every store. Prefer a complete basket (every item in stock). Then lowest total, then shorter distance.
2. **Cheapest split.** Try every subset of stores up to `max_stores` (fine for 12 stores and k ≤ 3). Each item goes to the cheapest in-stock store in the subset. Add that store's delivery fee on the subtotal actually bought there. Items unavailable at every store in the subset stay in the result as missing. They are never dropped.
3. **Nearest store.** Lowest `distance_km`, even if some items are missing.

Savings for a complete strategy are its total subtracted from the most expensive complete single-store total. Incomplete strategies report savings as null.

The recommended key is the complete strategy with the lowest total, breaking ties toward fewer stores.

### Budget

- Spent = sum of `actual` expenses in the month.
- Planned = sum of `planned` expenses.
- Committed = actual + planned.
- Remaining = total − committed.
- Projected month-end = actual spend so far × days in the month / days elapsed. Before the month, the projection is 0. On or after the last day, it equals actual spend. Planned money is not mixed into the pace.
- Warnings: committed above 80% and above 100% of the total budget, and the same tests for each category limit. Exactly 80% does not warn. Exactly 100% warns as high use, and only a ratio above 1 warns as over budget.

Recording a basket asks the server to re-estimate the chosen strategy and write one expense per item, plus one expense per store delivery fee. The client does not send amounts. An incomplete strategy is rejected.

### Fit to budget

If the recommended complete total is above the remaining budget, the service suggests:

- a same-category swap whose per-unit price is lower, buying enough packs to cover the original base quantity
- reducing a quantity that is above 1
- removing a line

Each suggestion includes the server-computed new total.

### Insights

- Cheapest store is the cheapest complete single store for the generated "Monthly family staples" basket.
- Price drops compare the earliest and latest price inside the month of the newest price row (November 2026 in the sample).
- Savings achieved reconstruct quantity from the stored line amount and the historical unit price, then compare that shop with the most expensive store on the same date. Delivery rows are excluded.

## API

Documented in `docs/API.md`. Errors are `{"error": "...", "details": {...}}` with 400, 404, 409, or 422 as appropriate.

## Pages

| Page | Behaviour |
| --- | --- |
| `index.html` | What the app does, quick search, largest recent drops |
| `compare.html` | Filter by name, category, brand, and stock. Sort by name, pack price, or per-unit price |
| `product.html` | Every store, per-unit price, cheapest in-stock store, stock, history chart |
| `lists.html` | List CRUD, sample lists, per-store totals, three strategies, record a basket |
| `budget.html` | Month budget, category limits, progress, projection, warnings, category chart, fit helper |
| `insights.html` | Cheapest store, drops, savings achieved |
| `admin.html` | Product, store, category, and price maintenance. Price CSV import with a row-level report. CSV export |

`js/components/navbar.js` injects the only navigation bar. `js/api.js` is the only place that calls `fetch`.

## Phases

1. Docs, schema, and deterministic data.
2. Money, units, optimiser, budget, and CSV services, with unit tests.
3. Flask API and API tests.
4. Frontend pages.
5. Full pytest run, seed, smoke test, and a browser pass.

## Limitations

- No accounts or authentication. The admin page is open on purpose for a local tool.
- Sample prices are generated. They are internally consistent, not scraped.
- One currency per process. Changing the symbol does not convert historical paise.
- The split search is exact brute force and is bounded to 12 stores and 3 stores per plan.
- Chart.js receives major-unit numbers already converted by the API so it can draw an axis. Those numbers are not a second price engine.
- Reseeding deletes lists, budgets, and expenses.
