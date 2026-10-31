"""HTTP and server contracts against a migrated PostgreSQL database."""

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

from fastapi import Depends
from fastapi.testclient import TestClient
from sqlalchemy import func, select, text
from sqlalchemy.orm import Session

from src.apis.examples.python.get_widgets import GetWidgets
from src.data.example.widgets.python.models import Owner, Widget
from src.data.python.postgresql.config import engine_from_file


class DatabaseTest(unittest.TestCase):
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

    def test_database_widgets_http(self):
        app = GetWidgets(self.engine).app
        client = TestClient(app)
        empty = client.get("/widgets")
        self.assertEqual(empty.status_code, 200)
        self.assertEqual(empty.json(), [])
        owner = Owner(id=uuid4(), name="account")
        widgets = [self.widget(owner), self.widget(owner)]
        widgets[1].name = "second widget"
        expected = [
            {"id": str(widget.id), "name": widget.name, "owner": "account"}
            for widget in sorted(widgets, key=lambda widget: widget.id)
        ]
        with Session(self.engine) as session, session.begin():
            session.add_all(widgets)
        self.assertEqual(client.get("/readyz").json(), {"ready": True})
        response = client.get("/widgets")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), expected)
        self.assertEqual(response.headers["x-content-type-options"], "nosniff")
        self.assertEqual(client.get("/database/widgets").status_code, 404)
        self.assertEqual(client.get("/missing").status_code, 404)
        secure = TestClient(app, base_url="https://testserver")
        self.assertEqual(
            secure.get("/readyz").headers["strict-transport-security"], "max-age=31536000"
        )

    def test_request_session_rolls_back_uncommitted_work(self):
        api = GetWidgets(self.engine)

        @api.app.post("/uncommitted")
        def uncommitted(fail: bool = False, session: Session = Depends(api.database_session)):
            session.add(Owner(id=uuid4(), name="uncommitted"))
            session.flush()
            if fail:
                raise ValueError("request failed")
            return {"ok": True}

        client = TestClient(api.app)
        self.assertEqual(client.post("/uncommitted").json(), {"ok": True})
        with self.assertRaisesRegex(ValueError, "request failed"):
            client.post("/uncommitted?fail=true")
        with Session(self.engine) as session:
            self.assertEqual(session.scalar(select(func.count()).select_from(Owner)), 0)

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
