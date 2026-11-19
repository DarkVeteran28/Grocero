from app.services.csv_importer import parse_price_csv


def test_price_csv_accepts_good_rows_and_reports_bad_ones():
    text = (
        "product_id,store_id,price,date,in_stock\n"
        "1,1,10.00,2026-11-01,true\n"
        "1,1,0,2026-11-02,true\n"
        "9,1,5,not-a-date,yes\n"
    )
    rows, errors = parse_price_csv(text, {1}, {1})
    assert len(rows) == 1
    assert rows[0]["price"] == 1000
    assert rows[0]["in_stock"] is True
    assert errors[0]["row"] == 3
    assert "greater than 0" in errors[0]["reason"]
    assert errors[1]["row"] == 4
    assert "product_id not found" in errors[1]["reason"]
    assert "date must be YYYY-MM-DD" in errors[1]["reason"]


def test_price_csv_rejects_a_bad_header():
    rows, errors = parse_price_csv("name,price\nMilk,10\n", {1}, {1})
    assert rows == []
    assert errors[0]["row"] == 1
