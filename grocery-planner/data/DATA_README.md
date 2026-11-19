# Sample data

These CSVs are **generated sample data**, not prices from a real shop. `generate_data.py` builds them with random seed `42`. Weekly prices run for 26 weeks and end on 16 November 2026. Larger packs of the same product are cheaper per kilogram, per litre, or per piece than smaller packs at the same store on the same day. Prices are never zero or negative. Each product is stocked at 4–8 of the 10 stores. About 4% of rows are out of stock, and a few more on the final week.

Replace the files and run `python scripts/seed.py` from `backend/` to load them. Seeding **deletes** the existing SQLite database, including shopping lists, budgets, and expenses.

Money in the CSVs is in rupees with up to two decimal places. The database stores paise.

## stores.csv

| Column | Required | Notes |
| --- | --- | --- |
| store_id | yes | Integer primary key |
| name | yes | |
| type | yes | `supermarket`, `local kirana`, `online`, or `wholesale` |
| area | yes | Neighbourhood or `Online` |
| distance_km | yes | Zero or greater |
| delivery_fee | yes | Rupees. `0.00` is allowed |
| free_delivery_above | no | Rupees. Leave blank if delivery is never free |
| rating | yes | 0 to 5 |

## categories.csv

| Column | Required |
| --- | --- |
| category_id | yes |
| name | yes, unique |

## products.csv

| Column | Required | Notes |
| --- | --- | --- |
| product_id | yes | |
| name | yes | Pack name without the brand |
| brand | yes | |
| category_id | yes | Must exist in categories.csv |
| pack_size | yes | Label such as `1 kg` or `500 ml` |
| unit | yes | `kg`, `g`, `L`, `ml`, or `piece` |
| base_unit_qty | yes | Pack size in kilograms, litres, or pieces. `500 g` → `0.5`, `750 ml` → `0.75`, a dozen eggs → `12` |

Per-unit price is the pack price divided by `base_unit_qty`.

## prices.csv

| Column | Required | Notes |
| --- | --- | --- |
| product_id | yes | Must exist |
| store_id | yes | Must exist |
| price | yes | Rupees, greater than 0, at most 2 decimal places |
| date | yes | `YYYY-MM-DD` |
| in_stock | yes | `true` or `false` |

One row per product, store, and date. Importing the same key again updates that row. The current price is the latest date. The admin page imports this file only: valid rows are saved and invalid rows are reported with a row number. A full catalogue reload still goes through `seed.py`.

## sample_lists.csv

| Column | Required | Notes |
| --- | --- | --- |
| list_name | yes | |
| product_id | yes | |
| quantity | yes | Number of packs, greater than 0 |
| product_name | no | Ignored by the loader. Helpful when editing by hand |
| pack_size | no | Ignored by the loader |

## Regenerate

```bash
python data/generate_data.py
cd backend && python scripts/seed.py
```
