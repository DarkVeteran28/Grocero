# Entity relationship

```mermaid
erDiagram
    categories ||--o{ products : classifies
    categories ||--o{ category_budgets : limits
    categories ||--o{ expenses : tags
    stores ||--o{ prices : sells
    stores ||--o{ expenses : checkout
    products ||--o{ prices : priced_on
    products ||--o{ shopping_list_items : includes
    products ||--o{ expenses : purchased
    shopping_lists ||--o{ shopping_list_items : contains
    shopping_lists ||--o{ expenses : records
    budgets ||--o{ category_budgets : splits

    stores {
        int id PK
        string name
        string type
        string area
        numeric distance_km
        int delivery_fee
        int free_delivery_above
        numeric rating
    }
    categories {
        int id PK
        string name
    }
    products {
        int id PK
        string name
        string brand
        int category_id FK
        string pack_size
        string unit
        numeric base_unit_qty
    }
    prices {
        int id PK
        int product_id FK
        int store_id FK
        int price
        date date
        bool in_stock
    }
    shopping_lists {
        int id PK
        string name
        datetime created_at
    }
    shopping_list_items {
        int id PK
        int list_id FK
        int product_id FK
        numeric quantity
    }
    budgets {
        int id PK
        string month
        int total_amount
    }
    category_budgets {
        int id PK
        int budget_id FK
        int category_id FK
        int limit_amount
    }
    expenses {
        int id PK
        date date
        int list_id FK
        int product_id FK
        int store_id FK
        int amount
        int category_id FK
        string status
    }
```

Money columns are integer paise. `prices.price`, item `quantity`, and `base_unit_qty` are constrained to be greater than zero. The current price of a product at a store is the row with the greatest `date`.
