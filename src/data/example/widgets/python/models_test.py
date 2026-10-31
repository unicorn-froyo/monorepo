"""Model contracts on a real Flyway-migrated PostgreSQL database."""

import unittest
from datetime import UTC, datetime
from decimal import Decimal
from uuid import uuid4

from psycopg import Error as PsycopgError
from sqlalchemy import func, inspect, select, text
from sqlalchemy.exc import IntegrityError, ProgrammingError
from sqlalchemy.orm import Session

from src.data.example.widgets.python.models import Outbox, Owner, Widget
from src.data.python.postgresql.config import engine_from_file


class ModelsTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.engine = engine_from_file()

    @classmethod
    def tearDownClass(cls):
        cls.engine.dispose()

    def setUp(self):
        with self.engine.begin() as connection:
            connection.execute(text("DELETE FROM outbox"))
            connection.execute(text("DELETE FROM widgets"))
            connection.execute(text("DELETE FROM owners"))

    def widget(self, owner):
        return Widget(
            id=uuid4(),
            owner=owner,
            name="雪☃",
            version=2**60 + 1,
            amount=Decimal("1234567890123456789012.12345678"),
            payload=b"\x00\xff",
            details={"value": "unicode 雪", "present": False},
            created_at=datetime(2026, 10, 29, 12, 0, 0, 123456, tzinfo=UTC),
            optional_text=None,
        )

    def test_exact_types_relationships_and_transactions(self):
        tables = inspect(self.engine).get_table_names(schema="widgets")
        owner = Owner(id=uuid4(), name="account")
        widget = self.widget(owner)
        identifier = widget.id
        expected = (
            widget.version,
            widget.amount,
            widget.payload,
            widget.details,
            widget.created_at,
        )
        with Session(self.engine) as session, session.begin():
            session.add(widget)
            session.flush()
            session.add(Outbox(id=uuid4(), widget_id=identifier, event_type="created"))
        with Session(self.engine) as session:
            stored = session.get(Widget, identifier)
            self.assertIsNotNone(stored)
            assert stored is not None
            self.assertEqual(
                (stored.version, stored.amount, stored.payload, stored.details, stored.created_at),
                expected,
            )
            self.assertIsNone(stored.optional_text)
            self.assertEqual(stored.owner.widgets, [stored])
        self.assertEqual(inspect(self.engine).get_table_names(schema="widgets"), tables)

        with self.assertRaisesRegex(RuntimeError, "rollback"):
            with Session(self.engine) as session, session.begin():
                second = self.widget(Owner(id=uuid4(), name="rollback"))
                session.add(second)
                session.flush()
                session.add(Outbox(id=uuid4(), widget_id=second.id, event_type="created"))
                session.flush()
                raise RuntimeError("rollback")
        with Session(self.engine) as session:
            for model in (Owner, Widget, Outbox):
                self.assertEqual(session.scalar(select(func.count()).select_from(model)), 1)

    def test_constraint_errors_and_application_role(self):
        with self.assertRaises(IntegrityError):
            with Session(self.engine) as session, session.begin():
                widget = self.widget(Owner(id=uuid4(), name="invalid"))
                widget.version = 0
                session.add(widget)
        for command in ("CREATE TABLE forbidden (id int)", "SELECT * FROM flyway_schema_history"):
            with self.assertRaises(ProgrammingError):
                with self.engine.begin() as connection:
                    connection.execute(text(command))
        with Session(self.engine) as session:
            self.assertEqual(session.scalar(select(func.count()).select_from(Owner)), 0)

        with self.assertRaises(IntegrityError) as conflict:
            with Session(self.engine) as session, session.begin():
                session.add_all(
                    [Owner(id=uuid4(), name="duplicate"), Owner(id=uuid4(), name="duplicate")]
                )
        assert isinstance(conflict.exception.orig, PsycopgError)
        self.assertEqual(conflict.exception.orig.sqlstate, "23505")
        with self.assertRaises(IntegrityError) as missing_parent:
            with Session(self.engine) as session, session.begin():
                session.add(Outbox(id=uuid4(), widget_id=uuid4(), event_type="created"))
        assert isinstance(missing_parent.exception.orig, PsycopgError)
        self.assertEqual(missing_parent.exception.orig.sqlstate, "23503")
        with self.assertRaises(IntegrityError) as null_value:
            with self.engine.begin() as connection:
                connection.execute(
                    text("INSERT INTO owners (id, display_name) VALUES (:id, NULL)"),
                    {"id": uuid4()},
                )
        assert isinstance(null_value.exception.orig, PsycopgError)
        self.assertEqual(null_value.exception.orig.sqlstate, "23502")


if __name__ == "__main__":
    unittest.main()
