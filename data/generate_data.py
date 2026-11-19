"""Deterministic sample grocery data.

Seed 42. Weekly prices end on 16 November 2026 (26 weeks).
Larger packs of the same product are always cheaper per unit at the same store on the same day.
"""

import csv
import random
from collections import defaultdict
from datetime import date, timedelta
from decimal import Decimal, ROUND_FLOOR, ROUND_HALF_UP
from pathlib import Path

SEED = 42
END = date(2026, 11, 16)
WEEKS = [END - timedelta(days=7 * (25 - index)) for index in range(26)]
NOV_2 = date(2026, 11, 2)
NOV_9 = date(2026, 11, 9)
DATA_DIR = Path(__file__).resolve().parent

CATEGORIES = [
    "Rice & Grains",
    "Pulses",
    "Vegetables",
    "Fruits",
    "Dairy",
    "Oils",
    "Spices",
    "Snacks",
    "Beverages",
    "Household",
    "Personal Care",
    "Bakery",
]

# id, name, type, area, distance_km, delivery rupees, free-above rupees or "", rating, price factor
STORES = [
    (1, "FreshBasket Supermarket", "supermarket", "Koramangala", "2.40", "40.00", "799.00", "4.3", "1.02"),
    (2, "GreenCart Online", "online", "Online", "6.00", "25.00", "499.00", "4.1", "0.96"),
    (3, "Annapurna Kirana", "local kirana", "Jayanagar", "0.80", "15.00", "399.00", "4.6", "1.08"),
    (4, "Metro Wholesale", "wholesale", "Peenya", "9.50", "0.00", "", "4.0", "0.86"),
    (5, "DailyNeeds Mart", "supermarket", "Indiranagar", "3.10", "30.00", "599.00", "4.2", "1.00"),
    (6, "SpiceRoute Kirana", "local kirana", "Malleswaram", "1.50", "10.00", "299.00", "4.5", "1.06"),
    (7, "BigHaul Wholesale", "wholesale", "Yeshwanthpur", "7.20", "0.00", "", "3.9", "0.84"),
    (8, "QuickGrocer Online", "online", "Online", "5.50", "20.00", "399.00", "4.0", "0.98"),
    (9, "Lakeview Supermarket", "supermarket", "HSR Layout", "4.00", "35.00", "699.00", "4.4", "1.03"),
    (10, "Namma Kirana", "local kirana", "BTM Layout", "1.10", "0.00", "", "4.7", "1.10"),
]

SIZES = {
    "kg3": [("1 kg", "kg", Decimal("1")), ("5 kg", "kg", Decimal("5")), ("10 kg", "kg", Decimal("10"))],
    "kg2": [("1 kg", "kg", Decimal("1")), ("5 kg", "kg", Decimal("5"))],
    "g2": [("500 g", "g", Decimal("0.5")), ("1 kg", "kg", Decimal("1"))],
    "spice": [("100 g", "g", Decimal("0.1")), ("200 g", "g", Decimal("0.2"))],
    "ml2": [("500 ml", "ml", Decimal("0.5")), ("1 L", "L", Decimal("1"))],
    "oil": [("1 L", "L", Decimal("1")), ("5 L", "L", Decimal("5"))],
    "pc": [("1 pc", "piece", Decimal("1"))],
    "eggs": [("6 pcs", "piece", Decimal("6")), ("12 pcs", "piece", Decimal("12"))],
    "snack": [("150 g", "g", Decimal("0.15")), ("300 g", "g", Decimal("0.3"))],
    "drink": [("750 ml", "ml", Decimal("0.75")), ("2 L", "L", Decimal("2"))],
    "bar": [("1 pc", "piece", Decimal("1")), ("4 pcs", "piece", Decimal("4"))],
    "clean": [("500 ml", "ml", Decimal("0.5")), ("1 L", "L", Decimal("1"))],
    "butter": [("100 g", "g", Decimal("0.1")), ("500 g", "g", Decimal("0.5"))],
    "coffee": [("50 g", "g", Decimal("0.05")), ("100 g", "g", Decimal("0.1"))],
    "tea": [("250 g", "g", Decimal("0.25")), ("500 g", "g", Decimal("0.5"))],
    "paneer": [("200 g", "g", Decimal("0.2")), ("500 g", "g", Decimal("0.5"))],
}
SIZE_FACTORS = [Decimal("1"), Decimal("0.94"), Decimal("0.88")]

RAW = """
Rice & Grains|India Gate|Classic Basmati Rice|kg3|170
Rice & Grains|Daawat|Rozana Basmati Rice|kg2|125
Rice & Grains|Kohinoor|Tibar Basmati Rice|kg2|115
Rice & Grains|Lalitha|Sona Masoori Rice|kg3|72
Rice & Grains|Aashirvaad|Select Whole Wheat Atta|kg3|54
Rice & Grains|Pillsbury|Chakki Fresh Atta|kg2|56
Rice & Grains|Quaker|Oats|kg2|185
Rice & Grains|Bambino|Roasted Vermicelli|g2|95
Rice & Grains|India Gate|Brown Rice|kg2|160
Rice & Grains|MTR|Rava|kg2|64
Rice & Grains|Fortune|Besan|kg2|92
Rice & Grains|24 Mantra|Jaggery|g2|85
Rice & Grains|Dhampure|Sugar|kg2|46
Pulses|Tata Sampann|Toor Dal|kg2|168
Pulses|Tata Sampann|Moong Dal|kg2|162
Pulses|24 Mantra|Chana Dal|kg2|142
Pulses|Organic Tattva|Urad Dal|kg2|158
Pulses|Rajdhani|Rajma Chitra|kg2|176
Pulses|Tata Sampann|Kabuli Chana|kg2|148
Pulses|Organic Tattva|Masoor Dal|kg2|132
Pulses|Tata Sampann|Moong Whole|kg2|140
Vegetables|Local|Onion|kg2|42
Vegetables|Local|Potato|kg2|36
Vegetables|Local|Tomato|g2|48
Vegetables|Local|Carrot|g2|52
Vegetables|Local|Beans|g2|84
Vegetables|Local|Cabbage|pc|32
Vegetables|Local|Cauliflower|pc|45
Vegetables|Local|Palak|pc|18
Vegetables|Local|Capsicum|g2|96
Vegetables|Local|Ginger|g2|190
Vegetables|Local|Garlic|g2|210
Vegetables|Local|Cucumber|g2|38
Vegetables|Local|Beetroot|g2|55
Vegetables|Local|Lemon|pc|4
Fruits|Local|Robusta Banana|kg2|58
Fruits|Hill|Shimla Apple|kg2|190
Fruits|Nagpur|Orange|kg2|85
Fruits|Ratnagiri|Alphonso Mango|kg2|220
Fruits|Local|Pomegranate|kg2|165
Fruits|Local|Green Grapes|g2|110
Fruits|Local|Watermelon|pc|80
Fruits|Local|Papaya|kg2|48
Fruits|Local|Chikoo|kg2|72
Fruits|Local|Pineapple|pc|60
Dairy|Amul|Taaza Milk|ml2|58
Dairy|Nandini|Goodlife Milk|ml2|62
Dairy|Amul|Gold Milk|ml2|72
Dairy|Amul|Butter|butter|520
Dairy|Amul|Processed Cheese|paneer|680
Dairy|Milky Mist|Paneer|paneer|460
Dairy|Hatsun|Curd|g2|96
Dairy|Amul|Fresh Cream|ml2|320
Dairy|Amul|Ghee|ml2|620
Dairy|GRB|Ghee|ml2|680
Oils|Fortune|Sunflower Oil|oil|155
Oils|Sundrop|Sunflower Oil|oil|148
Oils|Fortune|Mustard Oil|ml2|185
Oils|Dhara|Groundnut Oil|oil|195
Oils|Parachute|Coconut Oil|ml2|210
Oils|Oleev|Active Oil|oil|230
Spices|MDH|Haldi Powder|spice|420
Spices|Everest|Chilli Powder|spice|460
Spices|MDH|Coriander Powder|spice|310
Spices|Catch|Garam Masala|spice|860
Spices|Tata|Salt|kg2|28
Spices|Aashirvaad|Salt|kg2|26
Spices|Everest|Cumin Powder|spice|720
Spices|MDH|Garam Masala|spice|940
Spices|MTR|Sambar Powder|spice|520
Spices|Everest|Chaat Masala|spice|680
Snacks|Britannia|Marie Gold|snack|180
Snacks|Parle|Parle-G|snack|160
Snacks|Lays|Classic Salted|snack|420
Snacks|Haldiram|Aloo Bhujia|snack|310
Snacks|Britannia|Good Day|snack|260
Snacks|Sunfeast|Dark Fantasy|bar|35
Snacks|Cadbury|Dairy Milk|bar|40
Snacks|Maggi|Masala Noodles|bar|15
Beverages|Nescafe|Classic Coffee|coffee|1800
Beverages|Bru|Instant Coffee|coffee|1600
Beverages|Tata|Tea Gold|tea|480
Beverages|Brooke Bond|Red Label Tea|tea|420
Beverages|Cadbury|Bournvita|g2|460
Beverages|Tropicana|Orange Juice|drink|140
Beverages|Real|Mixed Fruit Juice|drink|130
Beverages|Bisleri|Packaged Water|oil|20
Beverages|Dabur|Honey|ml2|650
Household|Surf Excel|Easy Wash|kg2|210
Household|Ariel|Matic|kg2|240
Household|Vim|Dishwash Liquid|clean|140
Household|Harpic|Toilet Cleaner|clean|160
Household|Comfort|Fabric Conditioner|clean|190
Household|Origami|Paper Napkins|pc|55
Household|Good Knight|Machine Refill|pc|90
Personal Care|Dove|Cream Beauty Soap|bar|42
Personal Care|Lifebuoy|Total Soap|bar|28
Personal Care|Colgate|Strong Teeth|spice|850
Personal Care|Closeup|Toothpaste|spice|780
Personal Care|Clinic Plus|Shampoo|clean|360
Personal Care|Pantene|Shampoo|clean|520
Personal Care|Dettol|Handwash|clean|280
Personal Care|Himalaya|Face Wash|pc|145
Personal Care|Colgate|Toothbrush|pc|30
Bakery|Britannia|Brown Bread|pc|48
Bakery|Modern|Milk Bread|pc|42
Bakery|Britannia|Pav|pc|32
Bakery|Harvest Gold|White Bread|pc|50
Bakery|Britannia|Fruit Cake|pc|30
Bakery|Farm Fresh|Eggs|eggs|8
Bakery|Country|Brown Eggs|eggs|12
"""

SAMPLES = [
    ("Weekly essentials", [
        ("Amul", "Taaza Milk", "1 L", "3"),
        ("Britannia", "Brown Bread", "1 pc", "2"),
        ("Farm Fresh", "Eggs", "6 pcs", "1"),
        ("Local", "Robusta Banana", "1 kg", "1"),
        ("Local", "Onion", "1 kg", "1"),
        ("Local", "Tomato", "1 kg", "1"),
        ("Tata", "Salt", "1 kg", "1"),
        ("Amul", "Butter", "100 g", "1"),
    ]),
    ("Monthly family staples", [
        ("India Gate", "Classic Basmati Rice", "5 kg", "2"),
        ("Aashirvaad", "Select Whole Wheat Atta", "5 kg", "2"),
        ("Tata Sampann", "Toor Dal", "1 kg", "2"),
        ("Fortune", "Sunflower Oil", "1 L", "2"),
        ("Tata", "Salt", "1 kg", "1"),
        ("Dhampure", "Sugar", "1 kg", "2"),
        ("Local", "Onion", "5 kg", "1"),
        ("Surf Excel", "Easy Wash", "1 kg", "1"),
        ("Amul", "Taaza Milk", "1 L", "8"),
        ("MDH", "Haldi Powder", "100 g", "1"),
        ("Everest", "Chilli Powder", "100 g", "1"),
    ]),
    ("Breakfast basics", [
        ("Quaker", "Oats", "1 kg", "1"),
        ("Amul", "Taaza Milk", "1 L", "2"),
        ("Britannia", "Brown Bread", "1 pc", "1"),
        ("Amul", "Butter", "100 g", "1"),
        ("Cadbury", "Bournvita", "500 g", "1"),
        ("Farm Fresh", "Eggs", "6 pcs", "1"),
    ]),
]


def _families():
    category_ids = {name: index + 1 for index, name in enumerate(CATEGORIES)}
    families = []
    for line in RAW.strip().splitlines():
        category, brand, name, size_key, base = [part.strip() for part in line.split("|")]
        families.append(
            {
                "category_id": category_ids[category],
                "brand": brand,
                "name": name,
                "sizes": SIZES[size_key],
                "base_paise": int(Decimal(base) * 100),
            }
        )
    return families


def _money(paise: int) -> str:
    return f"{Decimal(paise) / Decimal(100):.2f}"


def build_datasets(seed: int = SEED) -> dict:
    rng = random.Random(seed)
    families = _families()
    store_ids = [row[0] for row in STORES]
    factors = {row[0]: Decimal(row[8]) for row in STORES}
    for index, family in enumerate(families):
        count = 4 + (index % 5)
        family["stores"] = tuple(sorted(rng.sample(store_ids, count)))

    products = []
    prices = []
    next_id = 1
    nov2_index = WEEKS.index(NOV_2)
    nov9_index = WEEKS.index(NOV_9)
    nov16_index = WEEKS.index(END)
    for index, family in enumerate(families):
        week_factors = {}
        for store_id in family["stores"]:
            series = []
            for _week in WEEKS:
                noise = Decimal(rng.randrange(-300, 401)) / Decimal(10000)
                extra = Decimal("0.90") if rng.randrange(100) < 8 else Decimal("1")
                series.append((Decimal("1") + noise) * extra)
            if index % 6 == 0:
                anchor = series[nov2_index]
                series[nov9_index] = anchor * Decimal("0.85")
                series[nov16_index] = anchor * Decimal("0.85")
            week_factors[store_id] = series

        family_products = []
        for size_index, (pack, unit, qty) in enumerate(family["sizes"]):
            product_id = next_id
            next_id += 1
            product = {
                "product_id": product_id,
                "name": family["name"],
                "brand": family["brand"],
                "category_id": family["category_id"],
                "pack_size": pack,
                "unit": unit,
                "base_unit_qty": qty,
                "family": (family["brand"], family["name"]),
            }
            products.append(product)
            family_products.append(product)
            previous_prices = family_products[size_index - 1]["_week_prices"] if size_index else None
            week_prices = {}
            for store_id in family["stores"]:
                store_factor = factors[store_id]
                for week_index, week in enumerate(WEEKS):
                    per_unit = int(
                        (
                            Decimal(family["base_paise"])
                            * SIZE_FACTORS[size_index]
                            * store_factor
                            * week_factors[store_id][week_index]
                        ).quantize(Decimal("1"), rounding=ROUND_HALF_UP)
                    )
                    per_unit = max(per_unit, 1)
                    price = int((Decimal(per_unit) * qty).quantize(Decimal("1"), rounding=ROUND_HALF_UP))
                    price = max(price, 1)
                    if previous_prices is not None:
                        prev_price = previous_prices[(store_id, week)]
                        prev_qty = family["sizes"][size_index - 1][2]
                        actual = Decimal(price) / qty
                        previous = Decimal(prev_price) / prev_qty
                        if actual >= previous:
                            target = previous - Decimal(1)
                            price = int((target * qty).to_integral_value(rounding=ROUND_FLOOR))
                            price = max(price, 1)
                    out_of_stock = rng.randrange(100) < (8 if week == END else 4)
                    prices.append(
                        {
                            "product_id": product_id,
                            "store_id": store_id,
                            "price_paise": price,
                            "date": week,
                            "in_stock": not out_of_stock,
                        }
                    )
                    week_prices[(store_id, week)] = price
            product["_week_prices"] = week_prices

    lookup = {(row["brand"], row["name"], row["pack_size"]): row["product_id"] for row in products}
    samples = []
    for list_name, items in SAMPLES:
        for brand, name, pack, quantity in items:
            product_id = lookup[(brand, name, pack)]
            product = next(row for row in products if row["product_id"] == product_id)
            samples.append(
                {
                    "list_name": list_name,
                    "product_id": product_id,
                    "quantity": quantity,
                    "product_name": product["name"],
                    "pack_size": pack,
                }
            )
    return {
        "categories": [{"category_id": index + 1, "name": name} for index, name in enumerate(CATEGORIES)],
        "stores": [
            {
                "store_id": row[0],
                "name": row[1],
                "type": row[2],
                "area": row[3],
                "distance_km": row[4],
                "delivery_fee": row[5],
                "free_delivery_above": row[6],
                "rating": row[7],
            }
            for row in STORES
        ],
        "products": products,
        "prices": prices,
        "sample_lists": samples,
    }


def validate_datasets(datasets: dict) -> None:
    products = datasets["products"]
    prices = datasets["prices"]
    if not 8 <= len(datasets["stores"]) <= 12:
        raise AssertionError("store count out of range")
    if not 150 <= len(products) <= 250:
        raise AssertionError(f"product count {len(products)} out of range")
    if any(row["price_paise"] <= 0 for row in prices):
        raise AssertionError("non-positive price")
    by_product = defaultdict(set)
    observations = defaultdict(int)
    for row in prices:
        by_product[row["product_id"]].add(row["store_id"])
        observations[(row["product_id"], row["store_id"])] += 1
    for product_id, stores in by_product.items():
        if not 4 <= len(stores) <= 8:
            raise AssertionError(f"product {product_id} has {len(stores)} stores")
    if any(count != 26 for count in observations.values()):
        raise AssertionError("expected 26 weekly prices")
    in_stock = sum(1 for row in prices if row["in_stock"])
    if in_stock / len(prices) < Decimal("0.8"):
        raise AssertionError("too many out-of-stock rows")
    families = defaultdict(list)
    for product in products:
        families[product["family"]].append(product)
    price_index = {(row["product_id"], row["store_id"], row["date"]): row["price_paise"] for row in prices}
    for group in families.values():
        ordered = sorted(group, key=lambda row: row["base_unit_qty"])
        for left, right in zip(ordered, ordered[1:]):
            for store_id in by_product[left["product_id"]] & by_product[right["product_id"]]:
                for week in WEEKS:
                    left_per = Decimal(price_index[(left["product_id"], store_id, week)]) / left["base_unit_qty"]
                    right_per = Decimal(price_index[(right["product_id"], store_id, week)]) / right["base_unit_qty"]
                    if right_per >= left_per:
                        raise AssertionError(f"bulk pack not cheaper for {right['name']} on {week}")
    known = {row["product_id"] for row in products}
    if any(row["product_id"] not in known for row in datasets["sample_lists"]):
        raise AssertionError("sample list references a missing product")


def write_csvs(datasets: dict, out_dir: Path = DATA_DIR) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    _write(
        out_dir / "categories.csv",
        ["category_id", "name"],
        [[row["category_id"], row["name"]] for row in datasets["categories"]],
    )
    _write(
        out_dir / "stores.csv",
        ["store_id", "name", "type", "area", "distance_km", "delivery_fee", "free_delivery_above", "rating"],
        [
            [row["store_id"], row["name"], row["type"], row["area"], row["distance_km"], row["delivery_fee"], row["free_delivery_above"], row["rating"]]
            for row in datasets["stores"]
        ],
    )
    _write(
        out_dir / "products.csv",
        ["product_id", "name", "brand", "category_id", "pack_size", "unit", "base_unit_qty"],
        [
            [row["product_id"], row["name"], row["brand"], row["category_id"], row["pack_size"], row["unit"], format(row["base_unit_qty"], "f")]
            for row in datasets["products"]
        ],
    )
    _write(
        out_dir / "prices.csv",
        ["product_id", "store_id", "price", "date", "in_stock"],
        [
            [row["product_id"], row["store_id"], _money(row["price_paise"]), row["date"].isoformat(), "true" if row["in_stock"] else "false"]
            for row in datasets["prices"]
        ],
    )
    _write(
        out_dir / "sample_lists.csv",
        ["list_name", "product_id", "quantity", "product_name", "pack_size"],
        [[row["list_name"], row["product_id"], row["quantity"], row["product_name"], row["pack_size"]] for row in datasets["sample_lists"]],
    )


def _write(path: Path, header, rows):
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(header)
        writer.writerows(rows)


def main():
    datasets = build_datasets()
    validate_datasets(datasets)
    write_csvs(datasets)
    print(
        f"Wrote {len(datasets['stores'])} stores, {len(datasets['products'])} products, "
        f"{len(datasets['prices'])} prices to {DATA_DIR}"
    )


if __name__ == "__main__":
    main()
