"""Widget store queries against the shared PostgreSQL fixture."""

import unittest
from datetime import UTC, datetime
from decimal import Decimal
from uuid import UUID, uuid4

from sqlalchemy import event, text
from sqlalchemy.orm import Session

from src.data.example.widgets.python.models import Owner, Widget
from src.data.example.widgets.python.store import WidgetStore
from src.data.python.postgresql.config import engine_from_file


class StoreTest(unittest.TestCase):
    def test_lists_all_widgets_with_eager_owners_in_id_order(self):
        engine = engine_from_file()
        try:
            with engine.begin() as connection:
                for table in ("outbox", "widgets", "owners"):
                    connection.execute(text(f"DELETE FROM {table}"))
            with Session(engine) as session, session.begin():
                owner = Owner(id=uuid4(), name="account")
                session.add_all(
                    Widget(
                        id=UUID(int=index),
                        owner=owner,
                        name=f"widget {index}",
                        version=1,
                        amount=Decimal("1.00000000"),
                        payload=b"\x00\xff",
                        details={},
                        created_at=datetime.now(UTC),
                        optional_text=None,
                    )
                    for index in range(101, 0, -1)
                )
            queries = []

            def record_query(_conn, _cursor, statement, _parameters, _context, _executemany):
                queries.append(statement)

            event.listen(engine, "before_cursor_execute", record_query)
            try:
                with Session(engine) as session:
                    records = WidgetStore(session).list()
                # Owners must remain available after the session closes.
                self.assertEqual(
                    [record.id for record in records], [UUID(int=i) for i in range(1, 102)]
                )
                self.assertEqual([record.owner.name for record in records], ["account"] * 101)
                self.assertEqual(len(queries), 1)
            finally:
                event.remove(engine, "before_cursor_execute", record_query)
            with engine.begin() as connection:
                connection.execute(text("DELETE FROM widgets"))
            with Session(engine) as session:
                self.assertEqual(WidgetStore(session).list(), [])
        finally:
            engine.dispose()


if __name__ == "__main__":
    unittest.main()
