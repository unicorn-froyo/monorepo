"""Example FastAPI widgets service."""

from http import HTTPStatus

from fastapi import HTTPException, Response
from sqlalchemy import Engine, select
from sqlalchemy.orm import Session

from src.apis.python.abstract_api_base import AbstractApiBase
from src.data.example.widgets.python.models import Widget


class GetWidgets(AbstractApiBase):  # pylint: disable=too-few-public-methods
    """Widgets HTTP API."""

    def __init__(self, engine: Engine | None = None) -> None:
        self.engine = engine
        super().__init__(title="Widgets API")

    def configure_routes(self) -> None:
        """Register widget endpoints."""

        @self.app.get("/widgets", status_code=HTTPStatus.ACCEPTED.value)
        async def get_widgets(response: Response) -> list[object]:
            response.status_code = HTTPStatus.ACCEPTED.value
            return []

        @self.app.get("/database/widgets")
        def widgets() -> list[dict[str, str]]:
            if self.engine is None:
                raise HTTPException(status_code=503, detail="Database is not configured")
            with Session(self.engine) as session:
                return [
                    {"id": str(widget.id), "name": widget.name, "owner": widget.owner.name}
                    for widget in session.scalars(select(Widget).order_by(Widget.id))
                ]

        @self.app.get("/readyz")
        def ready() -> dict[str, bool]:
            if self.engine is not None:
                with self.engine.connect() as connection:
                    connection.execute(select(1))
            return {"ready": True}


app = GetWidgets().app
