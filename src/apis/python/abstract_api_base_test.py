"""Tests for the FastAPI API base class."""

import os
from asyncio import run
from unittest import TestCase, main
from unittest.mock import MagicMock, patch

from fastapi import Depends, Response
from fastapi.testclient import TestClient
from sqlalchemy import Engine, select
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import Session
from starlette.types import Message, Receive, Scope, Send

from src.apis.python.abstract_api_base import AbstractApiBase
from src.apis.python.security_headers import SecurityHeadersMiddleware


class TestApiBase(TestCase):
    """Tests for the framework-neutral ASGI entrypoint."""

    class Api(AbstractApiBase):  # pylint: disable=too-few-public-methods
        """Small API used by the tests."""

        def __init__(self, engine: Engine | None = None) -> None:
            super().__init__(title="Test API", engine=engine)

        def configure_routes(self) -> None:
            @self.app.get("/message")
            async def message() -> dict[str, str]:
                return {"message": "Hello world!"}

    def test_lifespan_without_database_configuration(self):
        """No database is opened when the process has no connection file."""
        with patch.dict(os.environ, {}, clear=True):
            with TestClient(self.Api().app) as client:
                self.assertEqual(client.get("/readyz").json(), {"ready": True})

    def test_lifespan_owns_configured_engine(self):
        """Startup is lazy and every shutdown releases the engine it created."""
        with patch.dict(os.environ, {"POSTGRES_CONNECTION_FILE": "/private/connection.json"}):
            with patch("src.apis.python.abstract_api_base.engine_from_file") as factory:
                for fail in (False, True):
                    with self.subTest(fail=fail):
                        factory.reset_mock()
                        api = self.Api()
                        factory.assert_not_called()
                        try:
                            with TestClient(api.app) as client:
                                factory.assert_called_once_with()
                                self.assertIs(api.engine, factory.return_value)
                                self.assertEqual(client.get("/readyz").status_code, 200)
                                if fail:
                                    raise ValueError("shutdown")
                        except ValueError:
                            self.assertTrue(fail)
                        factory.return_value.dispose.assert_called_once_with()
                        self.assertIsNone(api.engine)

    def test_startup_connection_failure_disposes_engine(self):
        """A bad configured connection fails startup and releases its pool."""
        with patch.dict(os.environ, {"POSTGRES_CONNECTION_FILE": "/private/connection.json"}):
            with patch("src.apis.python.abstract_api_base.engine_from_file") as factory:
                factory.return_value.connect.side_effect = OperationalError(
                    "SELECT 1", {}, Exception("unavailable")
                )
                api = self.Api()
                with self.assertRaises(OperationalError):
                    with TestClient(api.app):
                        self.fail("Startup accepted an unavailable database")
                factory.return_value.dispose.assert_called_once_with()
                self.assertIsNone(api.engine)

    def test_lifespan_borrows_injected_engine(self):
        """Explicit injection takes precedence over process configuration."""
        engine = MagicMock()
        with patch.dict(os.environ, {"POSTGRES_CONNECTION_FILE": "/unused"}):
            with patch("src.apis.python.abstract_api_base.engine_from_file") as factory:
                api = self.Api(engine)
                with TestClient(api.app) as client:
                    self.assertEqual(client.get("/readyz").status_code, 200)
                factory.assert_not_called()
        engine.dispose.assert_not_called()
        self.assertIs(api.engine, engine)

    def test_database_is_optional(self):
        """Ordinary APIs stay ready; database routes require configuration."""
        api = self.Api()

        @api.app.get("/database")
        def database(session: Session = Depends(api.database_session)):
            return {"active": session.is_active}

        client = TestClient(api.app)
        self.assertEqual(client.get("/readyz").json(), {"ready": True})
        response = client.get("/database")
        self.assertEqual(response.status_code, 503)
        self.assertEqual(response.json(), {"detail": "Database is not configured"})

    def test_request_sessions_close_on_success_and_failure(self):
        """Each request gets a session and failures reach its cleanup context."""
        engine = MagicMock()
        api = self.Api(engine)

        @api.app.get("/database")
        def database(fail: bool = False, session: Session = Depends(api.database_session)):
            session.scalar(select(1))
            if fail:
                raise ValueError("route failed")
            return {"ok": True}

        with patch("src.apis.python.abstract_api_base.Session") as factory:
            client = TestClient(api.app)
            self.assertEqual(client.get("/database").json(), {"ok": True})
            factory.return_value.__exit__.assert_called_once_with(None, None, None)
            with self.assertRaisesRegex(ValueError, "route failed"):
                client.get("/database?fail=true")
            self.assertEqual(factory.call_count, 2)
            factory.assert_called_with(engine)
            self.assertEqual(factory.return_value.__exit__.call_args.args[0], ValueError)
        engine.dispose.assert_not_called()

    def test_readiness_checks_database_and_propagates_failure(self):
        """A configured but unavailable database must not report ready."""
        engine = MagicMock()
        client = TestClient(self.Api(engine).app, raise_server_exceptions=False)
        self.assertEqual(client.get("/readyz").json(), {"ready": True})
        engine.connect.return_value.__enter__.return_value.execute.assert_called_once()
        engine.connect.side_effect = OperationalError("SELECT 1", {}, Exception("unavailable"))
        response = client.get("/readyz")
        self.assertEqual(response.status_code, 503)
        self.assertEqual(response.json(), {"ready": False})

    def test_is_abstract(self):
        """The base cannot be instantiated without route configuration."""
        with self.assertRaises(TypeError):
            # This deliberately invalid construction tests ABC's runtime check.
            AbstractApiBase(  # pyright: ignore[reportAbstractUsage]
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
        scopes: list[Scope] = []
        messages: list[Message] = []

        async def app(scope: Scope, receive: Receive, send: Send) -> None:
            scopes.append(scope)
            await send(await receive())

        async def receive() -> Message:
            return {"type": "lifespan.startup"}

        async def send(message: Message) -> None:
            messages.append(message)

        scope: Scope = {"type": "lifespan"}
        run(SecurityHeadersMiddleware(app)(scope, receive, send))
        self.assertEqual(scopes, [scope])
        self.assertEqual(messages, [{"type": "lifespan.startup"}])

    def test_overrides_unsafe_headers(self):
        """A route cannot accidentally undo the response policy."""
        app = self.Api().app
        client = TestClient(app, base_url="https://testserver")

        @app.get("/custom")
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
