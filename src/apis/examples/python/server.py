"""Container entrypoint for the widgets API."""

import argparse
import os

import uvicorn

from src.apis.examples.python.get_widgets import GetWidgets
from src.data.python.postgresql.config import engine_from_file

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", type=int, default=8080)
    args = parser.parse_args()
    engine = engine_from_file() if "POSTGRES_CONNECTION_FILE" in os.environ else None
    try:
        uvicorn.run(GetWidgets(engine).app, host="0.0.0.0", port=args.port)
    finally:
        if engine is not None:
            engine.dispose()
