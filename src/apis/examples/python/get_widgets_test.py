"""Tests for the example FastAPI widgets service."""

from types import SimpleNamespace
from unittest import TestCase, main
from unittest.mock import MagicMock, patch

from fastapi.testclient import TestClient

from src.apis.examples.python.get_widgets import GetWidgets, app


class TestGetWidgets(TestCase):
    """Widgets API tests."""

    def test_get_widgets(self):
        """An empty database returns an empty collection with the shared headers."""
        with patch("src.apis.python.abstract_api_base.Session") as session:
            session.return_value.__enter__.return_value.scalars.return_value = []
            response = TestClient(GetWidgets(MagicMock()).app).get("/widgets")

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


if __name__ == "__main__":
    main(verbosity=2)
