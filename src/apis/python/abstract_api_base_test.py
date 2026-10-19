"""Tests for the FastAPI API base class."""
from unittest import TestCase, main

from fastapi.testclient import TestClient

from src.apis.python.abstract_api_base import AbstractApiBase


class TestApiBase(TestCase):
    """Tests for the framework-neutral ASGI entrypoint."""

    class Api(AbstractApiBase):  # pylint: disable=too-few-public-methods
        """Small API used by the tests."""

        def __init__(self) -> None:
            super().__init__(title="Test API")

        def configure_routes(self) -> None:
            @self.app.get("/message")
            async def message() -> dict[str, str]:
                return {"message": "Hello world!"}

    def test_is_abstract(self):
        """The base cannot be instantiated without route configuration."""
        with self.assertRaises(TypeError):
            AbstractApiBase(  # pylint: disable=abstract-class-instantiated
                title="Test"
            )

    def test_exposes_fastapi_application(self):
        """The application handles normal HTTP requests through ASGI."""
        client = TestClient(self.Api().app)

        response = client.get("/message")

        self.assertEqual(response.status_code, 200)
        self.assertDictEqual(response.json(), {"message": "Hello world!"})

    def test_openapi_is_available(self):
        """FastAPI supplies the service's OpenAPI document."""
        client = TestClient(self.Api().app)

        response = client.get("/openapi.json")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["info"]["title"], "Test API")


if __name__ == "__main__":
    main(verbosity=2)
