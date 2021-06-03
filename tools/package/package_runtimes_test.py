"""Test Runtimes Enum"""
from unittest import TestCase, main

from tools.package.package_runtimes import LambdaRuntimes


class TestLambdaRuntimes(TestCase):
    """Test Runtimes Enum"""

    def test_runtimes(self):
        """Test Lambda Runtimes"""

        self.assertListEqual(
            LambdaRuntimes.values(), ["python", "nodejs", "go"]
        )


if __name__ == "__main__":
    main(verbosity=2)
