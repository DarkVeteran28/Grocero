# Smart Grocery Price Comparison and Budget Planner

Compare grocery prices across nearby stores, estimate a shopping list three ways, and track it against a monthly budget. The Flask API owns every price, delivery fee, and budget figure. The pages only collect input and show what the API returns.

Sample prices are generated. They are consistent (no zero prices, larger packs cheaper per unit) and are not a live shop feed.

## Folder structure

```
grocery-planner/
├── backend/          Flask app, services, tests, seed and smoke scripts
├── frontend/         HTML, CSS, ES modules, local Chart.js
├── data/             Generator, CSVs, and DATA_README.md
└── docs/             PLAN.md, API.md, ER diagram
```

Business rules live in `backend/app/services`. Routes stay thin. `frontend/js/api.js` is the only module that calls `fetch`. `frontend/js/components/navbar.js` is the only navigation bar.

## Setup and run

From the repository root:

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python scripts/seed.py
python run.py
```

Open http://127.0.0.1:5000 .

`seed.py` rebuilds `backend/instance/grocery.db` from `data/*.csv`. Running it again deletes lists, budgets, and expenses.

Tests, from `backend/`:

```bash
pytest
python scripts/smoke_test.py
```

## Currency

The symbol, thousands separator, and decimal places are set in `backend/app/config.py` (default ₹, commas, 2 decimals). Amounts are stored as integer paise. `GET /api/config` sends the display settings to the browser.

## Import real data

1. Follow the column rules in `data/DATA_README.md`.
2. Replace the CSVs in `data/` and run `python scripts/seed.py` for a full reload.
3. Or, on the Admin page, import a price CSV. Valid rows are inserted or updated. Invalid rows are reported with a row number and are skipped.
4. Products, stores, and categories can also be added on the Admin page. Export buttons download the current tables as CSV.

Regenerate the bundled sample with `python data/generate_data.py` (seed 42, 26 weeks ending 16 November 2026).

## API summary

| Method | Path | Purpose |
| --- | --- | --- |
| GET | `/api/config` | Currency and today's month |
| GET | `/api/categories` | Categories |
| GET | `/api/products` | Search, filter, sort |
| GET | `/api/products/<id>` | Pack prices at every store |
| GET | `/api/products/<id>/prices` | History for the chart |
| GET | `/api/stores` | Stores and delivery terms |
| POST | `/api/lists` | Create a list |
| GET, PUT, DELETE | `/api/lists/<id>` | Read, replace, or delete a list |
| POST | `/api/lists/<id>/estimate` | Single store, split, and nearest totals |
| GET, POST | `/api/budgets` | List or create a month budget |
| GET | `/api/budgets/<month>/summary` | Spent, remaining, projection, warnings |
| POST | `/api/prices/import` | Validate and import price rows |
| GET | `/api/insights` | Cheapest staples store, drops, savings |
| GET | `/api/admin/export/<name>.csv` | Download stores, products, prices, or categories |

Errors are `{"error": "...", "details": ...}` with status 200, 201, 400, 404, 409, or 422. The full contract is `docs/API.md`.

## Pages

- **Home** explains the three buying strategies and links a search to Compare. It lists the largest recent drops.
- **Compare** filters by name, category, brand, and stock, and sorts by pack price or per-unit price.
- **Product** shows every store, highlights the cheapest in-stock price, and charts weekly pack prices.
- **My Lists** creates and edits lists, loads a sample, and prices the basket per store. The three strategies are cheapest single store, cheapest split across 1–3 stores (delivery included), and nearest store. Incomplete baskets name the missing items. A complete strategy can be recorded as planned or actual.
- **Budget** sets a month total and optional category limits, shows a progress bar, category chart, pace to month-end, and warnings above 80% and above 100%. Fit to budget suggests cheaper same-category swaps or smaller quantities, with the new total calculated on the server.
- **Insights** names the cheapest store for the monthly staples basket, the biggest drops in the latest price month, and savings on recorded actual purchases.
- **Admin** edits products, stores, and prices, imports a price CSV with a row-level error report, and exports CSV.

## Known limitations

- There is no login. The admin tools are open on this local app.
- Prices are a generated sample, not scraped from shops.
- One currency per process. Changing the symbol does not convert stored paise.
- Split search is exact and limited to 12 stores and 3 stores in a plan.
- Chart.js plots major-unit numbers produced by the API.
- Reseeding wipes shopping lists, budgets, and expenses.
- Savings on the insights page are reconstructed from the recorded line amount and that day's shelf prices.
- Tax is not modelled. Distance is the value stored for the store, not a live map route.
