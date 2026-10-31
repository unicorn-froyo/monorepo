"""Example FastAPI widgets service."""

from http import HTTPStatus

from fastapi import Depends, Response
from sqlalchemy import Engine, select
from sqlalchemy.orm import Session

from src.apis.python.abstract_api_base import AbstractApiBase
from src.data.example.widgets.python.models import Widget


class GetWidgets(AbstractApiBase):  # pylint: disable=too-few-public-methods
    """Widgets HTTP API."""

    def __init__(self, engine: Engine | None = None) -> None:
        super().__init__(title="Widgets API", engine=engine)

    def configure_routes(self) -> None:
        """Register widget endpoints."""

        @self.app.get("/widgets", status_code=HTTPStatus.ACCEPTED.value)
        async def get_widgets(response: Response) -> list[object]:
            response.status_code = HTTPStatus.ACCEPTED.value
            return []

        @self.app.get("/database/widgets")
        def widgets(session: Session = Depends(self.database_session)) -> list[dict[str, str]]:
            return [
                {"id": str(widget.id), "name": widget.name, "owner": widget.owner.name}
                for widget in session.scalars(select(Widget).order_by(Widget.id))
            ]


app = GetWidgets().app
