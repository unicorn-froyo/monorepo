"""FastAPI base class for HTTP APIs."""

import os
from abc import ABC, abstractmethod
from collections.abc import AsyncIterator, Iterator
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from sqlalchemy import Engine, select
from sqlalchemy.orm import Session

from src.apis.python.security_headers import SecurityHeadersMiddleware
from src.data.python.postgresql.config import engine_from_file


class AbstractApiBase(ABC):  # pylint: disable=too-few-public-methods
    """Base for APIs served by an ASGI server.

    Subclasses register their routes in :meth:`configure_routes`. The exposed
    ``app`` is a regular FastAPI application and can be served by Uvicorn or
    any other ASGI server.
    """

    def __init__(self, *, title: str, version: str = "1.0.0", engine: Engine | None = None) -> None:
        self.engine = engine
        self.app = FastAPI(title=title, version=version, lifespan=self.lifespan)
        self.app.add_middleware(SecurityHeadersMiddleware)
        self.app.get("/readyz")(self.ready)
        self.configure_routes()

    @asynccontextmanager
    async def lifespan(self, _app: FastAPI) -> AsyncIterator[None]:
        """Own configured engines for the app lifetime; injected engines are borrowed."""
        owned_engine = None
        if self.engine is None and "POSTGRES_CONNECTION_FILE" in os.environ:
            owned_engine = engine_from_file()
            self.engine = owned_engine
        try:
            yield
        finally:
            if owned_engine is not None:
                owned_engine.dispose()
                self.engine = None

    def database_session(self) -> Iterator[Session]:
        """Yield one request's session; callers explicitly own their transactions.

        Closing rolls back unfinished transactions, including when a route fails.
        Engines created at startup are disposed at shutdown; injected engines
        remain owned by their caller.
        """
        if self.engine is None:
            raise HTTPException(status_code=503, detail="Database is not configured")
        with Session(self.engine) as session:
            yield session

    def ready(self) -> dict[str, bool]:
        """Check the configured database before reporting service readiness."""
        if self.engine is not None:
            with self.engine.connect() as connection:
                connection.execute(select(1))
        return {"ready": True}

    @abstractmethod
    def configure_routes(self) -> None:
        """Register this API's routes on ``self.app``."""
