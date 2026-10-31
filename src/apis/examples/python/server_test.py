"""Server startup, live database access, and shutdown contracts."""

import json
import os
import re
import signal
import subprocess
import time
import unittest
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path
from urllib.error import URLError
from urllib.request import urlopen
from uuid import uuid4

from sqlalchemy import text
from sqlalchemy.orm import Session

from src.data.example.widgets.python.models import Owner, Widget
from src.data.python.postgresql.config import engine_from_file


class TestServer(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.engine = engine_from_file()

    @classmethod
    def tearDownClass(cls):
        cls.engine.dispose()

    def setUp(self):
        with self.engine.begin() as connection:
            connection.execute(text("DELETE FROM outbox"))
            connection.execute(text("DELETE FROM widgets"))
            connection.execute(text("DELETE FROM owners"))

    def widget(self, owner):
        return Widget(
            id=uuid4(),
            owner=owner,
            name="雪☃",
            version=2**60 + 1,
            amount=Decimal("1234567890123456789012.12345678"),
            payload=b"\x00\xff",
            details={"value": "unicode 雪", "present": False},
            created_at=datetime(2026, 10, 29, 12, 0, 0, 123456, tzinfo=UTC),
            optional_text=None,
        )

    def test_service_process_connects_to_injected_postgres(self):
        owner = Owner(id=uuid4(), name="account")
        widget = self.widget(owner)
        identifier = widget.id
        with Session(self.engine) as session, session.begin():
            session.add(widget)
        server = Path("src/apis/examples/python/server").resolve()
        log = Path(os.environ["TEST_UNDECLARED_OUTPUTS_DIR"]) / "service.log"
        with log.open("w") as output:
            process = subprocess.Popen(
                [str(server), "--port=0"], stdout=output, stderr=subprocess.STDOUT
            )
            try:
                deadline = time.monotonic() + 20
                while time.monotonic() < deadline:
                    match = re.search(r"http://0\.0\.0\.0:(\d+)", log.read_text())
                    if match:
                        try:
                            with urlopen(
                                f"http://127.0.0.1:{match[1]}/readyz", timeout=1
                            ) as response:
                                self.assertEqual(json.load(response), {"ready": True})
                            break
                        except URLError:
                            pass
                    if process.poll() is not None:
                        self.fail(log.read_text())
                    time.sleep(0.05)
                else:
                    self.fail("Service did not become ready: " + log.read_text())
                # An update after startup proves the process reads live database state.
                with self.engine.begin() as connection:
                    connection.execute(
                        text("UPDATE widgets SET display_name = :name WHERE id = :id"),
                        {"name": "updated 雪", "id": identifier},
                    )
                assert match is not None
                with urlopen(f"http://127.0.0.1:{match[1]}/widgets", timeout=5) as response:
                    self.assertEqual(response.status, 200)
                    self.assertEqual(
                        json.load(response),
                        [{"id": str(identifier), "name": "updated 雪", "owner": "account"}],
                    )
            finally:
                process.terminate()
                self.assertIn(process.wait(timeout=10), (0, -signal.SIGTERM))
                self.assertIn("Application shutdown complete", log.read_text())

    def test_service_process_rejects_missing_connection_file(self):
        server = Path("src/apis/examples/python/server").resolve()
        missing = Path(os.environ["TEST_TMPDIR"]) / "missing-connection.json"
        result = subprocess.run(
            [str(server), "--port=0"],
            env={**os.environ, "POSTGRES_CONNECTION_FILE": str(missing)},
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("Application startup failed", result.stderr)


if __name__ == "__main__":
    unittest.main()
