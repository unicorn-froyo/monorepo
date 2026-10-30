"""Run the PostgreSQL-backed example with an injected runtime connection file."""

import argparse

import uvicorn

from src.apis.examples.python.database_app import create_app
from src.data.python.postgresql.config import engine_from_file

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", type=int, default=8080)
    args = parser.parse_args()
    engine = engine_from_file()
    try:
        uvicorn.run(create_app(engine), host="127.0.0.1", port=args.port)
    finally:
        engine.dispose()
