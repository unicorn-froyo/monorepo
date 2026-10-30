"""Explicit SQLAlchemy engines from a private runtime connection file."""

import json
import os
from pathlib import Path

from sqlalchemy import URL, Engine, create_engine


def engine_from_file(path: Path | None = None) -> Engine:
    """Build a bounded pool without implicitly creating or migrating any tables."""
    settings = json.loads((path or Path(os.environ["POSTGRES_CONNECTION_FILE"])).read_text())
    if settings["format_version"] != 1:
        raise ValueError("Unsupported PostgreSQL connection format")
    port = settings["port"]
    if type(port) is not int or not 1 <= port <= 65535:
        raise ValueError("Invalid PostgreSQL port")
    if settings["sslmode"] not in ("disable", "require", "verify-ca", "verify-full"):
        raise ValueError("Unsupported PostgreSQL TLS policy")
    url = URL.create(
        "postgresql+psycopg",
        username=settings["user"],
        password=settings["password"],
        host=settings["host"],
        port=port,
        database=settings["database"],
        query={"sslmode": settings["sslmode"], "connect_timeout": "5"},
    )
    return create_engine(
        url, pool_size=5, max_overflow=0, pool_timeout=5, pool_pre_ping=True, hide_parameters=True
    )
