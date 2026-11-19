"""Register blueprints."""

from app.routes.admin import bp as admin_bp
from app.routes.budgets import bp as budgets_bp
from app.routes.insights import bp as insights_bp
from app.routes.lists import bp as lists_bp
from app.routes.prices import bp as prices_bp
from app.routes.products import bp as products_bp
from app.routes.stores import bp as stores_bp


def register_blueprints(app):
    for blueprint in (products_bp, stores_bp, lists_bp, budgets_bp, prices_bp, insights_bp, admin_bp):
        app.register_blueprint(blueprint)
