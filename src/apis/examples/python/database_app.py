"""Example ORM-backed endpoints sharing the ordinary API middleware."""

from fastapi import FastAPI
from sqlalchemy import Engine, select
from sqlalchemy.orm import Session

from src.apis.examples.python.get_widgets import GetWidgets
from src.data.example.widgets.python.models import Widget


def create_app(engine: Engine) -> FastAPI:
    """Inject an engine; schema creation and migration remain outside startup."""
    app = GetWidgets().app

    @app.get("/database/widgets")
    def widgets() -> list[dict[str, str]]:
        with Session(engine) as session:
            return [
                {"id": str(widget.id), "name": widget.name, "owner": widget.owner.name}
                for widget in session.scalars(select(Widget).order_by(Widget.id))
            ]

    @app.get("/readyz")
    def ready() -> dict[str, bool]:
        with engine.connect() as connection:
            connection.execute(select(1))
        return {"ready": True}

    return app
