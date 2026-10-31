"""Connection settings must remain explicit, exact, and safe to log."""

import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from sqlalchemy.pool import QueuePool

from src.data.python.postgresql.config import engine_from_file


class ConfigTest(unittest.TestCase):
    def test_engine_url_and_validation(self):
        settings = dict(
            format_version=1,
            host="localhost",
            port=5432,
            database="testdb",
            user="app",
            password="x@:/?#",
            sslmode="verify-full",
        )
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "connection.json"
            path.write_text(json.dumps(settings))
            engine = engine_from_file(path)
            self.assertEqual(engine.url.password, settings["password"])
            self.assertNotIn(settings["password"], str(engine.url))
            self.assertIsInstance(engine.pool, QueuePool)
            assert isinstance(engine.pool, QueuePool)
            self.assertEqual(engine.pool.size(), 5)
            engine.dispose()
            with patch.dict(os.environ, {"POSTGRES_CONNECTION_FILE": str(path)}):
                engine_from_file().dispose()
            for key, value in (
                ("format_version", 2),
                ("port", "5432"),
                ("port", 0),
                ("port", 65536),
                ("sslmode", "prefer"),
            ):
                with self.subTest(key=key, value=value):
                    path.write_text(json.dumps(dict(settings, **{key: value})))
                    with self.assertRaises(ValueError):
                        engine_from_file(path)


if __name__ == "__main__":
    unittest.main()
