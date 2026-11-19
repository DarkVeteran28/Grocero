"""Process configuration. Money is stored as paise; these fields only change display."""

import os
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
BACKEND_DIR = REPO_ROOT / "backend"
FRONTEND_DIR = REPO_ROOT / "frontend"
DATA_DIR = REPO_ROOT / "data"
INSTANCE_DIR = BACKEND_DIR / "instance"

CURRENCY_SYMBOL = "₹"
CURRENCY_CODE = "INR"
DECIMAL_PLACES = 2
THOUSANDS_SEPARATOR = ","
PAISE_PER_UNIT = 100


class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY", "grocery-planner-dev")
    SQLALCHEMY_DATABASE_URI = os.environ.get("DATABASE_URL") or (
        "sqlite:///" + str(INSTANCE_DIR / "grocery.db")
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    JSON_SORT_KEYS = False
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024
    FRONTEND_DIR = str(FRONTEND_DIR)
    DATA_DIR = str(DATA_DIR)
    CURRENCY_SYMBOL = CURRENCY_SYMBOL
    CURRENCY_CODE = CURRENCY_CODE
    DECIMAL_PLACES = DECIMAL_PLACES
    THOUSANDS_SEPARATOR = THOUSANDS_SEPARATOR
    PAISE_PER_UNIT = PAISE_PER_UNIT
