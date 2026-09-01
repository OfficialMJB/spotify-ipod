"""HTML page routes."""

from flask import Blueprint, current_app, render_template

pages_blueprint = Blueprint("pages", __name__)


@pages_blueprint.get("/")
def index() -> str:
    return render_template(
        "index.html", display_name=current_app.config["DISPLAY_NAME"]
    )


@pages_blueprint.get("/health")
def health() -> tuple[dict[str, str], int]:
    return {"status": "ok"}, 200
