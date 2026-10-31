"""Fixture lifecycle, cleanup, credentials, and command failure contracts."""

import json
import os
import subprocess
import sys
import tempfile
import unittest
from contextlib import contextmanager
from pathlib import Path
from unittest.mock import MagicMock, patch

import psycopg

from tools.testing.python import postgresql as pg


class FixtureTest(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.root = Path(self.directory.name)
        self.sql = self.root / "V1__create.sql"
        self.sql.write_text("CREATE TABLE widget (id INT);\n")
        self.bundle = dict(
            sql_files=[str(self.sql)], script_configs=[], schema="widgets", history_table="history"
        )
        manifest = self.root / "bundle.json"
        manifest.write_text(json.dumps(self.bundle))
        image = self.root / "image.tar"
        image.write_bytes(b"oci")
        self.fixture = dict(
            migrations=str(manifest),
            image=str(image),
            database="testdb",
            flyway="cli",
            image_load_timeout_seconds=120,
            startup_timeout_seconds=1,
            migration_timeout_seconds=1,
        )
        self.client = MagicMock()
        self.container = self.client.containers.run.return_value
        self.container.attrs = {"NetworkSettings": {"Ports": {"5432/tcp": [{"HostPort": "15432"}]}}}
        self.container.logs.return_value = b"postgresql ready"
        self.client.containers.list.return_value = [self.container]
        self.connection = dict(host="localhost", port=5432, database="testdb")

    def test_image_import_restores_api_timeout_on_success_and_failure(self):
        self.client.api.timeout = 10

        def loaded(archive):
            self.assertEqual(self.client.api.timeout, 120)
            self.assertEqual(archive.read(), b"oci")
            return ["image"]

        self.client.images.load.side_effect = loaded
        self.assertEqual(pg.load_image(self.root / "image.tar", self.client, 120), "image")
        self.assertEqual(self.client.api.timeout, 10)
        self.client.images.load.side_effect = RuntimeError("import failed")
        with self.assertRaisesRegex(RuntimeError, "import failed"):
            pg.load_image(self.root / "image.tar", self.client, 120)
        self.assertEqual(self.client.api.timeout, 10)

    def test_private_json_is_exclusive_and_restrictive(self):
        path = self.root / "secret.json"
        pg.private_json(path, {"password": "secret"})
        self.assertEqual(path.stat().st_mode & 0o777, 0o600)
        self.assertEqual(json.loads(path.read_text()), {"password": "secret"})
        with self.assertRaises(FileExistsError):
            pg.private_json(path, {})

    def test_ready_retries_authentication_and_bounds_wait(self):
        with (
            patch.object(pg.psycopg, "connect") as connect,
            patch.object(pg.time, "sleep") as sleep,
        ):
            connect.side_effect = [psycopg.OperationalError(), MagicMock()]
            pg.wait_ready(self.connection, "secret", float("inf"))
            sleep.assert_called_once_with(0.1)
            connect.side_effect = psycopg.OperationalError()
            with self.assertRaises(TimeoutError):
                pg.wait_ready(self.connection, "secret", 0)

    def test_application_grants_use_separate_role(self):
        with patch.object(pg.psycopg, "connect") as connect:
            pg.grant_application(self.connection, "admin", "appsecret", self.bundle)
            calls = connect.return_value.__enter__.return_value.execute.call_args_list
            self.assertEqual(len(calls), 8)
            self.assertEqual(connect.call_args.kwargs["user"], "postgres")

    def test_flyway_declared_inputs_flags_redaction_and_failure(self):
        config = Path(str(self.sql) + ".conf")
        config.write_text("executeInTransaction=false")
        self.bundle["script_configs"] = [str(config)]
        with patch.object(pg.subprocess, "run") as run:
            run.side_effect = [
                subprocess.CompletedProcess(
                    [], 0, stdout='{"success": true}', stderr="secret migration\n"
                ),
                subprocess.CompletedProcess(
                    [], 0, stdout='{"validationSuccessful": true}', stderr=""
                ),
            ]
            pg.run_flyway(self.fixture, self.bundle, self.connection, "secret", self.root)
            self.assertEqual(run.call_count, 2)
            self.assertTrue((self.root / "migrations" / config.name).is_file())
            self.assertEqual(run.call_args.args[0][-1], "validate")
            self.assertNotIn("secret", (self.root / "flyway.log").read_text())
            self.assertIn("-cleanDisabled=true", run.call_args.args[0])
            failure_root = self.root / "failure"
            failure_root.mkdir()
            run.side_effect = None
            run.return_value = subprocess.CompletedProcess(
                [], 1, stdout='{"error": "invalid SQL"}', stderr=""
            )
            with self.assertRaisesRegex(RuntimeError, "Flyway migrate failed"):
                pg.run_flyway(self.fixture, self.bundle, self.connection, "secret", failure_root)

    def test_flyway_rejects_unsuccessful_zero_exit_and_invalid_result(self):
        for index, report in enumerate(('{"success": false}', "{}", "[]")):
            root = self.root / str(index)
            root.mkdir()
            with patch.object(
                pg.subprocess,
                "run",
                return_value=subprocess.CompletedProcess([], 0, stdout=report, stderr=""),
            ):
                with self.assertRaisesRegex(RuntimeError, "Flyway migrate failed"):
                    pg.run_flyway(self.fixture, self.bundle, self.connection, "secret", root)

    def test_success_and_test_failure_always_remove_resources(self):
        for fail in (False, True):
            with self.subTest(fail=fail):
                for path in self.root.glob("*connection.json"):
                    path.unlink()
                with (
                    patch.object(pg, "wait_ready"),
                    patch.object(pg, "run_flyway"),
                    patch.object(pg, "grant_application"),
                ):
                    try:
                        with pg.postgres(self.fixture, self.root, self.client) as env:
                            path = Path(env["POSTGRES_CONNECTION_FILE"])
                            settings = json.loads(path.read_text())
                            self.assertEqual(settings["port"], 15432)
                            self.assertEqual(settings["user"], "app")
                            self.assertEqual(path.stat().st_mode & 0o777, 0o600)
                            if fail:
                                raise RuntimeError("test failed")
                    except RuntimeError as error:
                        self.assertEqual(str(error), "test failed")
                self.container.remove.assert_called_with(force=True, v=True)
                self.client.networks.create.return_value.remove.assert_called()

    def test_pre_container_and_migration_failure_cleanup(self):
        self.client.images.load.side_effect = RuntimeError("load failed")
        with self.assertRaisesRegex(RuntimeError, "load failed"):
            with pg.postgres(self.fixture, self.root, self.client):
                self.fail("fixture yielded after failed startup")
        self.client.networks.create.return_value.remove.assert_called_once()
        self.client.images.load.side_effect = None
        with (
            patch.object(pg, "wait_ready"),
            patch.object(pg, "run_flyway", side_effect=RuntimeError("bad migration")),
        ):
            with self.assertRaisesRegex(RuntimeError, "bad migration"):
                with pg.postgres(self.fixture, self.root, self.client):
                    self.fail("fixture yielded after failed migration")
        self.container.remove.assert_called_with(force=True, v=True)

    def test_logs_failure_still_cleans_resources(self):
        self.container.logs.side_effect = RuntimeError("logs unavailable")
        with (
            patch.object(pg, "wait_ready"),
            patch.object(pg, "run_flyway"),
            patch.object(pg, "grant_application"),
        ):
            with self.assertRaisesRegex(RuntimeError, "logs unavailable"):
                with pg.postgres(self.fixture, self.root, self.client):
                    pass
        self.container.remove.assert_called_once()
        self.client.networks.create.return_value.remove.assert_called_once()

    def test_run_retains_logs_and_coverage_status_without_secrets(self):
        @contextmanager
        def fixture(_spec, root, _client):
            (root / "flyway.log").write_text("migration diagnostics")
            (root / "connection.json").write_text("secret")
            yield {"POSTGRES_CONNECTION_FILE": str(root / "connection.json")}

        output = self.root / "output"
        with (
            patch.dict(
                os.environ,
                {"TEST_UNDECLARED_OUTPUTS_DIR": str(output), "TEST_TMPDIR": str(self.root)},
            ),
            patch.object(pg, "postgres", fixture),
            patch.object(pg.subprocess, "call", return_value=7) as call,
        ):
            self.assertEqual(pg.run(self.fixture, ["coverage"], self.client), 7)
            self.assertEqual((output / "flyway.log").read_text(), "migration diagnostics")
            self.assertFalse((output / "connection.json").exists())
            self.assertIn("POSTGRES_CONNECTION_FILE", call.call_args.kwargs["env"])

    def test_main_and_cancellation(self):
        manifest = self.root / "fixture.json"
        manifest.write_text(json.dumps(self.fixture))
        args = ["postgresql", "--fixture", str(manifest), "--", "coverage"]
        with (
            patch.object(sys, "argv", args),
            patch.object(pg.signal, "signal"),
            patch.object(pg.docker, "from_env"),
            patch.object(pg, "run", return_value=4) as run,
        ):
            self.assertEqual(pg.main(), 4)
            run.side_effect = RuntimeError("failed")
            self.assertEqual(pg.main(), 2)
            run.side_effect = KeyboardInterrupt()
            self.assertEqual(pg.main(), 130)
        with patch.object(sys, "argv", args[:-2]), self.assertRaises(SystemExit):
            pg.main()
        with self.assertRaises(KeyboardInterrupt):
            pg.interrupted(15, None)

    def test_development_and_explicit_recovery(self):
        with patch.object(pg, "postgres") as fixture, patch.object(pg.signal, "pause"):
            fixture.return_value.__enter__.return_value = {
                "POSTGRES_CONNECTION_FILE": "/private/connection.json",
                "POSTGRES_TEST_LABEL": "label",
            }
            self.assertEqual(pg.dev(self.fixture, self.client), 0)
        with self.assertRaises(ValueError):
            pg.cleanup("arbitrary-container", self.client)
        identity = "bazel-postgres-" + "a" * 32
        network = MagicMock()
        self.client.networks.list.return_value = [network]
        pg.cleanup(identity, self.client)
        self.container.remove.assert_called_once_with(force=True, v=True)
        network.remove.assert_called_once()
        self.assertEqual(
            self.client.networks.list.call_args.kwargs["filters"],
            {"label": f"{pg.LABEL}={identity}"},
        )

    def test_main_dev_recovery_and_missing_fixture(self):
        manifest = self.root / "fixture.json"
        manifest.write_text(json.dumps(self.fixture))
        with (
            patch.object(sys, "argv", ["pg", "--fixture", str(manifest), "--dev"]),
            patch.object(pg.signal, "signal"),
            patch.object(pg.docker, "from_env"),
            patch.object(pg, "dev", return_value=0) as dev,
        ):
            self.assertEqual(pg.main(), 0)
            dev.side_effect = KeyboardInterrupt()
            self.assertEqual(pg.main(), 0)
        with (
            patch.object(sys, "argv", ["pg", "--cleanup-run", "label"]),
            patch.object(pg.signal, "signal"),
            patch.object(pg.docker, "from_env"),
            patch.object(pg, "cleanup") as cleanup,
        ):
            self.assertEqual(pg.main(), 0)
            cleanup.assert_called_once()
        with patch.object(sys, "argv", ["pg"]), self.assertRaises(SystemExit):
            pg.main()


if __name__ == "__main__":
    unittest.main()
