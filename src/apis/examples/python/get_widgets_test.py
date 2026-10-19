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


if __name__ == "__main__":
    main(verbosity=2)
