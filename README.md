# Smart Grocery Price Comparison & Budget Planner

A local web app for comparing grocery prices across nearby stores, planning a basket, and keeping monthly grocery spending on track. The app combines a Flask API, a SQLite database, and a browser interface served by the same local server.

> **Data note:** The included prices are generated sample data. They are useful for exploring the app, but they are not live prices from retailers.

## Contents

- [What you can do](#what-you-can-do)
- [How a shopping session works](#how-a-shopping-session-works)
- [Run locally](#run-locally)
- [Pages and features](#pages-and-features)
- [How the app works](#how-the-app-works)
- [Project layout](#project-layout)
- [Data and database](#data-and-database)
- [Developer commands](#developer-commands)
- [Known limitations](#known-limitations)
- [Further documentation](#further-documentation)

## What you can do

- Search a product catalogue and compare pack prices and normalized unit prices.
- Check current offers and stock status across stores, then view price history.
- Build and edit shopping lists, or start from a sample list.
- Compare a list using three strategies: buy from one store, split across stores, or use the nearest store.
- Include delivery fees and free-delivery thresholds in basket totals.
- Set a monthly budget and optional category limits; track planned and actual purchases.
- Get budget warnings, a month-end spending projection, and suggestions for bringing a basket within the remaining budget.
- Maintain catalogue data, import prices from CSV, and export tables from the Admin page.

## How a shopping session works

1. Search from **Home** or open **Compare** to find a product. Filter by category, brand, and stock, and sort by pack or unit price.
2. Open a product to compare its latest in-stock price at each store and review its price history.
3. Add products and quantities to **My Lists**. Estimate the basket to compare the cheapest complete single-store option, the cheapest split across up to three stores, and the nearest store. The estimate shows missing items and delivery charges.
4. Set a monthly budget in **Budget**. Record an estimate as planned or actual to include it in budget tracking. If a basket exceeds the remaining amount, ask the app for ways to reduce it.
5. Visit **Insights** for a staples-basket comparison, recent price drops, and savings from recorded actual purchases.

## Run locally

### Requirements

- Python 3.10 or newer
- `pip`

### Setup

From the repository root, create and activate a virtual environment, install the backend packages, and load the sample data:

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python scripts/seed.py
```

On Windows Command Prompt, activate the environment with `.venv\Scripts\activate.bat`. In PowerShell, use `.venv\Scripts\Activate.ps1`.

Start the app from the `backend/` directory:

```bash
python run.py
```

Open **http://127.0.0.1:5000** in your browser. Flask serves both the website and its API from this address. Stop the server with `Ctrl+C` in the terminal.

## Host with Docker

The included Docker setup runs the app with Gunicorn, exposes port `8080` by default, and stores SQLite data in a named volume so it survives container rebuilds.

1. Install Docker with Docker Compose support.
2. From the repository root, create a local environment file and set a unique secret:

   ```bash
   cp .env.example .env
   ```

   Replace the `SECRET_KEY` value in `.env` with a long random value before hosting.
3. Build and start the container:

   ```bash
   docker compose up --build -d
   ```

4. Open **http://localhost:8080**. The first start seeds the persistent database with the bundled sample data. Later starts keep the database as-is.

Useful commands:

```bash
docker compose logs -f web   # follow application logs
docker compose down          # stop containers; retain the database volume
```

Set `PORT` in `.env` to change the host port. The database lives in the Docker volume `grocery_data`; back up that volume before removing or migrating it. `docker compose down -v` deletes it, including saved lists, budgets, and expenses. The startup script sets the data directory permissions, then runs Gunicorn as the non-root app user (UID 10001).

### Deploy to Render

The repository includes [`render.yaml`](render.yaml) for a Render Blueprint. It builds the Docker image, binds to Render's `PORT`, generates `SECRET_KEY`, and mounts a persistent disk at `/data` for SQLite.

1. Push the repository to GitHub or another Git provider connected to Render.
2. In Render, choose **New → Blueprint**, connect the repository, and select the branch containing `render.yaml`.
3. Review the Blueprint. It creates a Singapore web service on Render's paid `0.5c-512mb` plan with a 1 GB persistent disk. Change the region or plan in `render.yaml` if needed, then apply it.
4. Wait for the first deploy to finish, then open the service URL shown on its Render dashboard.

The first boot initializes the mounted disk with the sample CSV data. Subsequent deploys preserve the database. Because Render disks are available only to paid web services, a free instance can be used only for a disposable demo: its SQLite changes are lost when the service restarts or deploys. A service with a persistent disk is limited to one instance and has a short interruption during deploys, so this SQLite setup is intended for a small single-instance app.

**Before sharing the public URL:** the app has no login, and its Admin page can edit shared catalogue and price data. Lists and budgets are also shared by every visitor. Treat this as a demo until authentication and per-user data access are added; do not store private information in it.

### About seeding

`python scripts/seed.py` creates the SQLite database at `backend/instance/grocery.db` and loads the bundled CSV data. **Seeding replaces the database** and deletes locally saved shopping lists, budgets, and expenses. Run it for a fresh setup or when you intentionally want to reset your local data; do not rerun it just to start the server.

## Pages and features

| Page | What it does |
| --- | --- |
| **Home** | Introduces the three shopping strategies, provides quick product search, and shows recent price drops. |
| **Compare** | Searches and filters products by name, category, brand, and stock. Sorts by name, pack price, or unit price. |
| **Product** | Shows pack details, current offers and availability at each store, the cheapest in-stock offer, and a weekly price-history chart. |
| **My Lists** | Creates, edits, and deletes lists; loads sample lists; estimates per-store totals and the three buying strategies; and records complete baskets as planned or actual. |
| **Budget** | Sets a monthly total and optional category limits, displays actual/planned/committed spending and remaining funds, projects month-end spending from actuals, shows warnings, and suggests basket changes to fit the budget. |
| **Insights** | Compares the sample monthly staples basket across stores, highlights recent drops, and summarizes savings from recorded actual purchases. |
| **Admin** | Adds and edits catalogue, store, category, and price data; imports price CSVs with row-level error feedback; and exports stores, categories, products, or prices. |

## How the app works

### Website and API

The browser pages are static HTML, CSS, and JavaScript modules in `frontend/`. They call the Flask JSON API at `/api/...`; the frontend and API share one origin. `frontend/js/api.js` centralizes browser API requests. Price, unit, delivery, basket, and budget calculations are performed by the backend, and the browser displays the returned results.

### Price comparison

Product offers use the latest recorded price for each product and store. The app shows both pack price and normalized price per kilogram, litre, or piece, so differently sized packs can be compared. Out-of-stock offers remain visible but are not treated as available buying options.

### Basket estimates

- **Cheapest single store:** finds the lowest total for a complete basket at one store.
- **Cheapest split:** assigns items across a selected maximum of one, two, or three stores to find the lowest complete total. Delivery is calculated for the items bought from each store.
- **Nearest store:** estimates the basket at the closest store, including any available items and identifying missing products.

Delivery fees are waived when the store subtotal reaches its free-delivery threshold. Incomplete strategies identify missing items; the app does not silently remove them. Savings are shown only for complete strategies.

### Budget tracking

Expenses can be **planned** or **actual**. Committed spending is the sum of both; the month-end projection uses actual spend and the number of elapsed days. When recording a basket, the server recalculates the chosen strategy and stores its item and delivery expenses. The browser does not submit its own total.

### Technology

- **Backend:** Python, Flask, Flask-SQLAlchemy, Flask-CORS
- **Database:** SQLite (`backend/instance/grocery.db` by default)
- **Frontend:** HTML, CSS, vanilla JavaScript ES modules
- **Charts:** locally bundled Chart.js
- **Tests:** pytest

Money is stored as integer paise (100 paise = ₹1); decimal arithmetic is used for quantity calculations. Currency display settings are in `backend/app/config.py`.

## Project layout

```text
.
├── backend/
│   ├── app/
│   │   ├── models/       # SQLAlchemy database models
│   │   ├── routes/       # HTTP endpoints
│   │   ├── services/     # Pricing, estimates, budgets, imports, insights
│   │   └── utils/        # Validation, errors, and money formatting
│   ├── scripts/          # CSV seeding and smoke check
│   ├── tests/            # API and service tests
│   └── run.py             # Local Flask server entry point
├── data/                  # Sample CSVs and deterministic data generator
├── docs/                  # API contract, project plan, and ER diagram
└── frontend/              # HTML pages, styles, JavaScript, and Chart.js
```

## Data and database

The bundled CSVs contain generated stores, categories, products, weekly prices, and sample lists. The generator uses a fixed seed, so its output is repeatable. See [`data/DATA_README.md`](data/DATA_README.md) for column formats and rules.

By default, the database is stored at `backend/instance/grocery.db`. To use a different database URL, set `DATABASE_URL` before starting the Flask app. For example, the application accepts a SQLAlchemy database URL; SQLite is the default. Set `SECRET_KEY` to override the development secret when needed.

To regenerate the sample CSV files and then reload the database:

```bash
python data/generate_data.py
cd backend
python scripts/seed.py
```

Reloading the database has the reset behavior described in [About seeding](#about-seeding).

## Developer commands

Run the test suite from `backend/` with the virtual environment active:

```bash
pytest
```

Run the API smoke check from `backend/`. It uses a temporary database and does not need the development server running:

```bash
python scripts/smoke_test.py
```

The API routes and request/response shapes are documented in [`docs/API.md`](docs/API.md). The service responsibilities and calculation rules are described in [`docs/PLAN.md`](docs/PLAN.md).

## Known limitations

- There are no user accounts; the Admin tools are open on the local app.
- Prices are generated examples, not scraped or live retailer prices.
- One currency is used per process. Changing the display symbol does not convert stored amounts.
- Store-splitting search is exact, with a limit of 12 stores and up to 3 stores per plan.
- Distance is the distance stored for the shop, not a live route from a map service.
- Tax is not modelled.

## Further documentation

- [API reference](docs/API.md)
- [Project plan and calculation details](docs/PLAN.md)
- [Entity-relationship diagram](docs/ER.md)
- [Sample data format](data/DATA_README.md)
