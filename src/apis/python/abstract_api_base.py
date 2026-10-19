"""FastAPI base class for HTTP APIs."""
from abc import ABC, abstractmethod

from fastapi import FastAPI


class AbstractApiBase(ABC):  # pylint: disable=too-few-public-methods
    """Base for APIs served by an ASGI server.

    Subclasses register their routes in :meth:`configure_routes`. The exposed
    ``app`` is a regular FastAPI application and can be served by Uvicorn or
    any other ASGI server.
    """

    def __init__(self, *, title: str, version: str = "1.0.0") -> None:
        self.app = FastAPI(title=title, version=version)
        self.configure_routes()

    @abstractmethod
    def configure_routes(self) -> None:
        """Register this API's routes on ``self.app``."""
