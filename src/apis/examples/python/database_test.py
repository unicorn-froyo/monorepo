"""HTTP and server contracts against a migrated PostgreSQL database."""

import json
import os
import re
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
        owner = Owner(id=uuid4(), name="account")
        widget = self.widget(owner)
        identifier = widget.id
        with Session(self.engine) as session, session.begin():
            session.add(widget)
        app = GetWidgets(self.engine).app
        client = TestClient(app)
        self.assertEqual(client.get("/readyz").json(), {"ready": True})
        response = client.get("/database/widgets")
        self.assertEqual(
            response.json(), [{"id": str(identifier), "name": "雪☃", "owner": "account"}]
        )
        self.assertEqual(response.headers["x-content-type-options"], "nosniff")
        self.assertEqual(client.get("/widgets").status_code, 202)
        self.assertEqual(client.get("/widgets").json(), [])
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
            finally:
                process.terminate()
                process.wait(timeout=10)


if __name__ == "__main__":
    unittest.main()
