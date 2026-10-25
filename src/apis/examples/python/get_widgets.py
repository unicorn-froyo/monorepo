"""Example FastAPI widgets service."""

from http import HTTPStatus

from fastapi import Response

from src.apis.python.abstract_api_base import AbstractApiBase


class GetWidgets(AbstractApiBase):  # pylint: disable=too-few-public-methods
    """Widgets HTTP API."""

    def __init__(self) -> None:
        super().__init__(title="Widgets API")

    def configure_routes(self) -> None:
        """Register widget endpoints."""

        @self.app.get("/widgets", status_code=HTTPStatus.ACCEPTED.value)
        async def get_widgets(response: Response) -> list[object]:
            response.status_code = HTTPStatus.ACCEPTED.value
            return []


app = GetWidgets().app
