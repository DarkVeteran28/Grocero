"""Insights for the dashboard page."""

from flask import Blueprint, jsonify

from app.services.insights import build_insights

bp = Blueprint("insights", __name__, url_prefix="/api")


@bp.get("/insights")
def insights():
    return jsonify(build_insights())
