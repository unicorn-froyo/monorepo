"""Tests for the example FastAPI widgets service."""

from unittest import TestCase, main

from fastapi.testclient import TestClient

from src.apis.examples.python.get_widgets import app


class TestGetWidgets(TestCase):
    """Widgets API tests."""

    def test_get_widgets(self):
        """The HTTP endpoint returns an accepted empty collection."""
        response = TestClient(app).get("/widgets")

        self.assertEqual(response.status_code, 202)
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


if __name__ == "__main__":
    main(verbosity=2)
