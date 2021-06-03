"""Supported Runtimes"""
from enum import Enum


class LambdaRuntimes(Enum):
    """Supported Runtimes"""

    PYTHON = "python"
    NODEJS = "nodejs"
    GOLANG = "go"

    @classmethod
    def values(cls) -> list:
        """Gets the list of enum values

        Returns:
            list: List of enum values
        """
        return list(map(lambda c: c.value, cls))
