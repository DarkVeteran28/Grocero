"""CSV downloads of the current database."""

from flask import Blueprint, Response

from app.services.csv_importer import export_csv
from app.utils.errors import ApiError

bp = Blueprint("admin", __name__, url_prefix="/api")


@bp.get("/admin/export/<string:dataset>")
def export_dataset(dataset):
    name = dataset.removesuffix(".csv")
    if name not in {"stores", "categories", "products", "prices"}:
        raise ApiError("Unknown export.", 404)
    body, filename = export_csv(name)
    return Response(
        body,
        mimetype="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )
