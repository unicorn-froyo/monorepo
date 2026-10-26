"""Container entrypoint for the widgets API."""

import uvicorn

if __name__ == "__main__":
    uvicorn.run(
        "src.apis.examples.python.get_widgets:app",
        host="0.0.0.0",
        port=8080,
    )
