"""Real migration failure, cleanup, and isolation tests against the pinned server."""

import json
import os
import tempfile
import unittest
from contextlib import closing
from pathlib import Path

import docker
import psycopg

from tools.testing.python import postgresql as pg


class LifecycleIntegrationTest(unittest.TestCase):
    def test_migration_failure_cleans_all_resources_and_retains_diagnostics(self):
        fixture = json.loads(Path("src/data/example/widgets/postgres.fixture.json").read_text())
        with (
            closing(docker.from_env(timeout=10)) as client,
            tempfile.TemporaryDirectory(dir=os.environ["TEST_TMPDIR"]) as directory,
        ):
            root = Path(directory)
            source = root / "V1__fail.sql"
            source.write_text("CREATE TABLE first_step (id INT);\nTHIS IS INVALID SQL;\n")
            bundle = json.loads(Path(fixture["migrations"]).read_text())
            bundle["sql_files"] = [str(source)]
            manifest = root / "bundle.json"
            manifest.write_text(json.dumps(bundle))
            fixture["migrations"] = str(manifest)
            with self.assertRaisesRegex(RuntimeError, "Flyway migrate failed"):
                with pg.postgres(fixture, root, client):
                    self.fail("Tests must not execute after failed migration")
            lifecycle = json.loads((root / "lifecycle.log").read_text())
            filters = {"label": f"{pg.LABEL}={lifecycle['run_id']}"}
            self.assertEqual(client.containers.list(all=True, filters=filters), [])
            self.assertEqual(client.networks.list(filters=filters), [])
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
        with (
            closing(docker.from_env(timeout=10)) as client,
            tempfile.TemporaryDirectory(dir=os.environ["TEST_TMPDIR"]) as directory,
        ):
            root = Path(directory)
            one, two = root / "one", root / "two"
            one.mkdir()
            two.mkdir()
            with (
                pg.postgres(fixture, one, client) as first,
                pg.postgres(fixture, two, client) as second,
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
