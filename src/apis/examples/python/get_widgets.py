"""Example FastAPI widgets service."""

from fastapi import Depends, HTTPException
from sqlalchemy import Engine
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from src.apis.python.abstract_api_base import AbstractApiBase
from src.data.example.widgets.python.store import WidgetStore


class GetWidgets(AbstractApiBase):  # pylint: disable=too-few-public-methods
    """Widgets HTTP API."""

    def __init__(self, engine: Engine | None = None) -> None:
        super().__init__(title="Widgets API", engine=engine)

    def configure_routes(self) -> None:
        """Register widget endpoints."""

        def widget_store(session: Session = Depends(self.database_session)) -> WidgetStore:
            return WidgetStore(session)

        @self.app.get("/widgets")
        def widgets(store: WidgetStore = Depends(widget_store)) -> list[dict[str, str]]:
            try:
                records = store.list()
            except SQLAlchemyError as error:
                raise HTTPException(status_code=500, detail="Database query failed") from error
            return [
                {"id": str(widget.id), "name": widget.name, "owner": widget.owner.name}
                for widget in records
            ]


app = GetWidgets().app
