"""Tests for the example FastAPI widgets service."""

from datetime import UTC, datetime
from decimal import Decimal
from types import SimpleNamespace
from unittest import TestCase, main
from unittest.mock import MagicMock, patch
from uuid import uuid4

from fastapi import Depends
from fastapi.testclient import TestClient
from sqlalchemy import func, select, text
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import Session

from src.apis.examples.python.get_widgets import GetWidgets, app
from src.data.example.widgets.python.models import Owner, Widget
from src.data.python.postgresql.config import engine_from_file


class TestGetWidgets(TestCase):
    """Widgets API tests."""

    def test_get_widgets(self):
        """An empty database returns an empty collection with the shared headers."""
        api = GetWidgets()
        session = MagicMock()
        session.scalars.return_value = []
        api.app.dependency_overrides[api.database_session] = lambda: session
        response = TestClient(api.app).get("/widgets")

        self.assertEqual(response.status_code, 200)
        self.assertListEqual(response.json(), [])
        self.assertEqual(response.headers["x-content-type-options"], "nosniff")
        self.assertEqual(response.headers["x-frame-options"], "DENY")
        self.assertEqual(response.headers["referrer-policy"], "no-referrer")
        self.assertEqual(
            response.headers["permissions-policy"],
            "camera=(), microphone=(), geolocation=()",
        )
        self.assertNotIn("strict-transport-security", response.headers)

    def test_https_uses_hsts(self):
        """The example honors the shared trusted-scheme header policy."""
        response = TestClient(app, base_url="https://testserver").get("/widgets")

        self.assertEqual(
            response.headers["strict-transport-security"],
            "max-age=31536000",
        )

    def test_optional_database_is_explicit(self):
        client = TestClient(app)
        self.assertEqual(client.get("/readyz").json(), {"ready": True})
        self.assertEqual(client.get("/widgets").status_code, 503)

    def test_injected_engine_is_used_by_the_same_application(self):
        engine = MagicMock()
        with patch("src.apis.python.abstract_api_base.Session") as session:
            session.return_value.__enter__.return_value.scalars.return_value = [
                SimpleNamespace(id="widget", name="display", owner=SimpleNamespace(name="owner"))
            ]
            client = TestClient(GetWidgets(engine).app)
            response = client.get("/widgets")
            self.assertEqual(response.status_code, 200)
            self.assertEqual(
                response.json(),
                [{"id": "widget", "name": "display", "owner": "owner"}],
            )
            self.assertEqual(client.get("/readyz").json(), {"ready": True})
            session.assert_called_once_with(engine)
            engine.connect.return_value.__enter__.return_value.execute.assert_called_once()

    def test_query_failure_returns_sanitized_error(self):
        with patch("src.apis.python.abstract_api_base.Session") as session:
            session.return_value.__enter__.return_value.scalars.side_effect = OperationalError(
                "private query", {}, Exception("private connection details")
            )
            response = TestClient(GetWidgets(MagicMock()).app).get("/widgets")
        self.assertEqual(response.status_code, 500)
        self.assertEqual(response.json(), {"detail": "Database query failed"})


class TestStoredWidgets(TestCase):
    """Widget HTTP behavior using the migrated PostgreSQL fixture."""

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

    def test_database_widgets_http(self):
        app = GetWidgets(self.engine).app
        client = TestClient(app)
        empty = client.get("/widgets")
        self.assertEqual(empty.status_code, 200)
        self.assertEqual(empty.json(), [])
        owner = Owner(id=uuid4(), name="account")
        widgets = [self.widget(owner), self.widget(owner)]
        widgets[1].name = "second widget"
        expected = [
            {"id": str(widget.id), "name": widget.name, "owner": "account"}
            for widget in sorted(widgets, key=lambda widget: widget.id)
        ]
        with Session(self.engine) as session, session.begin():
            session.add_all(widgets)
        self.assertEqual(client.get("/readyz").json(), {"ready": True})
        response = client.get("/widgets")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), expected)
        self.assertEqual(response.headers["x-content-type-options"], "nosniff")
        self.assertEqual(client.get("/database/widgets").status_code, 404)
        self.assertEqual(client.get("/missing").status_code, 404)
        secure = TestClient(app, base_url="https://testserver")
        self.assertEqual(
            secure.get("/readyz").headers["strict-transport-security"], "max-age=31536000"
        )

    def test_request_session_rolls_back_uncommitted_work(self):
        api = GetWidgets(self.engine)

        @api.app.post("/uncommitted")
        def uncommitted(fail: bool = False, session: Session = Depends(api.database_session)):
            session.add(Owner(id=uuid4(), name="uncommitted"))
            session.flush()
            if fail:
                raise ValueError("request failed")
            return {"ok": True}

        client = TestClient(api.app)
        self.assertEqual(client.post("/uncommitted").json(), {"ok": True})
        with self.assertRaisesRegex(ValueError, "request failed"):
            client.post("/uncommitted?fail=true")
        with Session(self.engine) as session:
            self.assertEqual(session.scalar(select(func.count()).select_from(Owner)), 0)


if __name__ == "__main__":
    main(verbosity=2)
