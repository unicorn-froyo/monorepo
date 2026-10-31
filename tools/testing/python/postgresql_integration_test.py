"""Real migration failure, cleanup, and isolation tests against the pinned server."""

import json
import os
import signal
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path

import psycopg

from tools.testing.python import postgresql as pg


class LifecycleIntegrationTest(unittest.TestCase):
    def test_cancellation_stops_database_and_test_child(self):
        with tempfile.TemporaryDirectory(dir=os.environ["TEST_TMPDIR"]) as directory:
            root = Path(directory)
            marker = root / "ready.json"
            child_tmp = root / "tmp"
            child_tmp.mkdir()
            output = root / "outputs"
            command = [
                str(Path("tools/testing/python/postgresql_runner").absolute()),
                "--fixture",
                "src/data/example/widgets/postgres.fixture.json",
                "--",
                sys.executable,
                "-c",
                "import json,os,pathlib,signal; "
                "settings=json.loads(pathlib.Path(os.environ['POSTGRES_CONNECTION_FILE']).read_text()); "
                "settings['pid']=os.getpid(); "
                "pathlib.Path(os.environ['READY_MARKER']).write_text(json.dumps(settings)); "
                "signal.pause()",
            ]
            with subprocess.Popen(
                command,
                env=dict(
                    os.environ,
                    TEST_TMPDIR=str(child_tmp),
                    TEST_UNDECLARED_OUTPUTS_DIR=str(output),
                    READY_MARKER=str(marker),
                ),
            ) as process:
                try:
                    deadline = time.monotonic() + 60
                    while not marker.exists():
                        self.assertIsNone(process.poll(), "fixture exited before starting tests")
                        self.assertLess(time.monotonic(), deadline, "fixture startup timed out")
                        time.sleep(0.05)
                    settings = json.loads(marker.read_text())
                    process.send_signal(signal.SIGTERM)
                    self.assertEqual(process.wait(timeout=15), 130)
                    lifecycle = json.loads((output / "lifecycle.log").read_text())
                    self.assertEqual(lifecycle["exit_code"], 0)
                    for pid in (settings["pid"], lifecycle["pid"]):
                        with self.assertRaises(ProcessLookupError):
                            os.kill(pid, 0)
                    self.assertEqual(list(child_tmp.iterdir()), [])
                finally:
                    pg.stop_process(process, signal.SIGTERM)

    def test_migration_failure_cleans_all_resources_and_retains_diagnostics(self):
        fixture = json.loads(Path("src/data/example/widgets/postgres.fixture.json").read_text())
        with tempfile.TemporaryDirectory(dir=os.environ["TEST_TMPDIR"]) as directory:
            root = Path(directory)
            source = root / "V1__fail.sql"
            source.write_text("CREATE TABLE first_step (id INT);\nTHIS IS INVALID SQL;\n")
            bundle = json.loads(Path(fixture["migrations"]).read_text())
            bundle["sql_files"] = [str(source)]
            manifest = root / "bundle.json"
            manifest.write_text(json.dumps(bundle))
            fixture["migrations"] = str(manifest)
            with self.assertRaisesRegex(RuntimeError, "Flyway migrate failed"):
                with pg.native_postgres(fixture, root):
                    self.fail("Tests must not execute after failed migration")
            lifecycle = json.loads((root / "lifecycle.log").read_text())
            self.assertEqual(lifecycle["exit_code"], 0)
            with self.assertRaises(ProcessLookupError):
                os.kill(lifecycle["pid"], 0)
            self.assertFalse((root / "data").exists())
            self.assertFalse((root / "admin-password").exists())
            diagnostics = (root / "flyway.log").read_text()
            (
                Path(os.environ["TEST_UNDECLARED_OUTPUTS_DIR"]) / "expected-migration-failure.log"
            ).write_text(diagnostics)
            report = json.loads(diagnostics)
            self.assertFalse(report["success"])
            self.assertEqual(report["error"]["sqlState"], "42601")
            self.assertEqual(report["migrationsExecuted"], 0)

    def test_simultaneous_fixtures_have_independent_databases(self):
        fixture = json.loads(Path("src/data/example/widgets/postgres.fixture.json").read_text())
        with tempfile.TemporaryDirectory(dir=os.environ["TEST_TMPDIR"]) as directory:
            root = Path(directory)
            one, two = root / "one", root / "two"
            one.mkdir()
            two.mkdir()
            with (
                pg.native_postgres(fixture, one) as first,
                pg.native_postgres(fixture, two) as second,
            ):
                settings = [
                    json.loads(Path(env["POSTGRES_CONNECTION_FILE"]).read_text())
                    for env in (first, second)
                ]
                self.assertNotEqual(settings[0]["port"], settings[1]["port"])
                for index, config in enumerate(settings):
                    config.pop("format_version")
                    config["dbname"] = config.pop("database")
                    with psycopg.connect(**config) as connection:
                        self.assertEqual(
                            connection.execute("SELECT count(*) FROM owners").fetchone(), (0,)
                        )
                        connection.execute(
                            "INSERT INTO owners (id, display_name) VALUES ('00000000-0000-0000-0000-000000000001', %s)",
                            [f"fixture-{index}"],
                        )
                        self.assertEqual(
                            connection.execute("SELECT display_name FROM owners").fetchone(),
                            (f"fixture-{index}",),
                        )
