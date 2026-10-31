"""Widget queries using a request-owned SQLAlchemy session."""

from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from src.data.example.widgets.python.models import Widget


class WidgetStore:
    """Query the Flyway-managed schema without owning sessions or transactions."""

    def __init__(self, session: Session) -> None:
        self.session = session

    def list(self) -> list[Widget]:
        """Load all widgets and their owners in stable ID order."""
        return list(
            self.session.scalars(
                select(Widget).options(joinedload(Widget.owner)).order_by(Widget.id)
            )
        )
