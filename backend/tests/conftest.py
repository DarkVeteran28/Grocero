"""Shared fixtures. The catalogue matches the hand-worked optimiser example."""

from datetime import date
from decimal import Decimal

import pytest
from sqlalchemy.pool import StaticPool

from app import create_app
from app.config import Config
from app.extensions import db
from app.models import Category, Price, Product, Store


class TestConfig(Config):
    TESTING = True
    SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"
    SQLALCHEMY_ENGINE_OPTIONS = {
        "connect_args": {"check_same_thread": False},
        "poolclass": StaticPool,
    }


@pytest.fixture()
def app():
    application = create_app(TestConfig)
    with application.app_context():
        db.create_all()
        dairy = Category(name="Dairy")
        grains = Category(name="Rice & Grains")
        db.session.add_all([dairy, grains])
        db.session.flush()
        db.session.add_all(
            [
                Store(name="NearMart", type="supermarket", area="Near", distance_km=Decimal("1.20"), delivery_fee=4000, free_delivery_above=20000, rating=Decimal("4.2")),
                Store(name="BudgetBazaar", type="supermarket", area="Mid", distance_km=Decimal("4.50"), delivery_fee=2000, free_delivery_above=15000, rating=Decimal("4.0")),
                Store(name="FarShop", type="wholesale", area="Far", distance_km=Decimal("8.00"), delivery_fee=0, free_delivery_above=None, rating=Decimal("3.8")),
            ]
        )
        db.session.flush()
        milk = Product(name="Milk", brand="Amul", category_id=dairy.id, pack_size="1 L", unit="L", base_unit_qty=Decimal("1"))
        rice = Product(name="Rice", brand="India Gate", category_id=grains.id, pack_size="1 kg", unit="kg", base_unit_qty=Decimal("1"))
        db.session.add_all([milk, rice])
        db.session.flush()
        latest = date(2026, 11, 16)
        earlier = date(2026, 11, 2)
        quotes = {
            milk.id: {1: 8000, 2: 6000, 3: 9000},
            rice.id: {1: 5000, 2: 7000, 3: 4000},
        }
        for product_id, stores in quotes.items():
            for store_id, price in stores.items():
                db.session.add(Price(product_id=product_id, store_id=store_id, price=price, date=latest, in_stock=True))
        db.session.add(Price(product_id=milk.id, store_id=1, price=8500, date=earlier, in_stock=True))
        db.session.commit()
        yield application
        db.session.remove()
        db.drop_all()


@pytest.fixture()
def client(app):
    return app.test_client()
