"""Container entrypoint for the widgets API."""

import argparse

import uvicorn

from src.apis.examples.python.get_widgets import GetWidgets

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", type=int, default=8080)
    args = parser.parse_args()
    uvicorn.run(GetWidgets().app, host="0.0.0.0", port=args.port)
