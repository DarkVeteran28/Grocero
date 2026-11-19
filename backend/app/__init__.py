"""Application factory. JSON API plus the static frontend."""

from pathlib import Path

from flask import Flask, jsonify, request, send_from_directory
from flask_cors import CORS
from werkzeug.exceptions import HTTPException, NotFound

from app.config import Config
from app.extensions import db
from app.utils.errors import ApiError


def create_app(config_class=None):
    app = Flask(__name__, static_folder=None)
    app.config.from_object(config_class or Config)
    Path(app.instance_path).mkdir(parents=True, exist_ok=True)
    db.init_app(app)
    CORS(app, resources={r"/api/*": {"origins": "*"}})

    from app import models  # noqa: F401
    from app.routes import register_blueprints

    register_blueprints(app)
    _register_errors(app)
    _register_frontend(app)
    return app


def _register_errors(app):
    @app.errorhandler(ApiError)
    def handle_api(err):
        return jsonify({"error": err.message, "details": err.details}), err.code

    @app.errorhandler(NotFound)
    def handle_404(err):
        if request.path.startswith("/api/"):
            return jsonify({"error": "Not found", "details": {}}), 404
        return ("Page not found", 404)

    @app.errorhandler(HTTPException)
    def handle_http(err):
        if request.path.startswith("/api/"):
            return jsonify({"error": err.name, "details": {}}), err.code
        return err


def _register_frontend(app):
    frontend = Path(app.config["FRONTEND_DIR"]).resolve()

    def send_nested(folder, filename):
        target = (frontend / folder / filename).resolve()
        root = (frontend / folder).resolve()
        if not str(target).startswith(str(root)) or not target.is_file():
            raise NotFound()
        return send_from_directory(root, filename)

    @app.get("/")
    def home_page():
        return send_from_directory(frontend, "index.html")

    @app.get("/<page>.html")
    def html_page(page):
        return send_nested(".", f"{page}.html")

    @app.get("/css/<path:filename>")
    def css_file(filename):
        return send_nested("css", filename)

    @app.get("/js/<path:filename>")
    def js_file(filename):
        return send_nested("js", filename)

    @app.get("/vendor/<path:filename>")
    def vendor_file(filename):
        return send_nested("vendor", filename)

    @app.get("/assets/<path:filename>")
    def asset_file(filename):
        return send_nested("assets", filename)
