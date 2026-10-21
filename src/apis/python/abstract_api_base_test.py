"""Tests for the FastAPI API base class."""
from asyncio import run
from unittest import TestCase, main

from fastapi import Response
from fastapi.testclient import TestClient

from src.apis.python.abstract_api_base import AbstractApiBase
from src.apis.python.security_headers import SecurityHeadersMiddleware


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

    def test_security_headers_on_routes_and_errors(self):
        """All HTTP responses have hardening headers, including 404s."""
        client = TestClient(self.Api().app)
        for path in ("/message", "/missing", "/openapi.json"):
            with self.subTest(path=path):
                response = client.get(path)
                self.assertEqual(response.headers["x-content-type-options"], "nosniff")
                self.assertEqual(response.headers["x-frame-options"], "DENY")
                self.assertEqual(response.headers["referrer-policy"], "no-referrer")
                self.assertEqual(
                    response.headers["permissions-policy"],
                    "camera=(), microphone=(), geolocation=()",
                )
                self.assertNotIn("strict-transport-security", response.headers)

    def test_hsts_only_on_https(self):
        """Do not advertise HSTS on local HTTP connections."""
        client = TestClient(self.Api().app, base_url="https://testserver")
        self.assertEqual(
            client.get("/missing").headers["strict-transport-security"],
            "max-age=31536000",
        )

    def test_non_http_scope_is_unchanged(self):
        """WebSocket and lifespan traffic passes through without modification."""
        scopes = []

        async def app(scope, _receive, _send):
            scopes.append(scope)

        scope = {"type": "lifespan"}
        run(SecurityHeadersMiddleware(app)(scope, app, app))
        self.assertEqual(scopes, [scope])

    def test_overrides_unsafe_headers(self):
        """A route cannot accidentally undo the response policy."""
        client = TestClient(self.Api().app, base_url="https://testserver")

        @client.app.get("/custom")
        async def custom():
            return Response(
                headers={"X-Frame-Options": "SAMEORIGIN", "Strict-Transport-Security": "max-age=0"}
            )

        response = client.get("/custom")
        self.assertEqual(response.headers["x-frame-options"], "DENY")
        self.assertEqual(response.headers["strict-transport-security"], "max-age=31536000")

    def test_openapi_is_available(self):
        """FastAPI supplies the service's OpenAPI document."""
        client = TestClient(self.Api().app)

        response = client.get("/openapi.json")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["info"]["title"], "Test API")


if __name__ == "__main__":
    main(verbosity=2)
