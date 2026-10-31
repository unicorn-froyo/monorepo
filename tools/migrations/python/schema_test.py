"""Real static linter and Flyway contract failures, without a database."""

import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from tools.migrations.python import schema


class SchemaTest(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.root = Path(self.directory.name)
        self.sql = self.root / "V01__first.sql"
        self.sql.write_text("CREATE TABLE widgets (id INTEGER PRIMARY KEY);\n")
        self.bundle = dict(
            sql_files=[str(self.sql)],
            script_configs=[],
            schema="widgets",
            history_table="flyway_schema_history",
        )
        self.config = Path("tools/migrations/flyway/sqlfluff.cfg")

    def test_lint_valid_invalid_and_unskippable_sql(self):
        self.assertEqual(schema.lint(self.bundle, self.config), [])
        self.sql.write_text("CREATE TABLE ( ; -- noqa\n")
        errors = schema.lint(self.bundle, self.config)
        self.assertTrue(any("PRS" in error for error in errors), errors)
        self.assertTrue(all(str(self.sql) in error for error in errors))
        # Intentionally larger than SQLFluff's default skip limit.
        self.sql.write_text("-- comment\n" * 3000 + "CREATE TABLE ( ;\n")
        self.assertTrue(schema.lint(self.bundle, self.config))

    def test_invalid_contracts(self):
        for overrides in (
            {"schema": "bad-name"},
            {"history_table": "Bad"},
            {"sql_files": []},
            {"sql_files": [str(self.root / "bad.sql")]},
            {"sql_files": [str(self.sql), str(self.root / "V1.0__duplicate.sql")]},
            {"script_configs": [str(self.root / "orphan.sql.conf")]},
        ):
            with self.subTest(overrides=overrides), self.assertRaises(ValueError):
                schema.validate(dict(self.bundle, **overrides))
        for text in ("", "SELECT '${secret}';"):
            self.sql.write_text(text)
            with self.assertRaises(ValueError):
                schema.validate(self.bundle)

    def test_script_configuration(self):
        config = Path(str(self.sql) + ".conf")
        self.bundle["script_configs"] = [str(config)]
        for value in ("executeInTransaction=true", "executeInTransaction=false"):
            config.write_text(value)
            self.assertEqual(schema.validate(self.bundle), [self.sql])
        config.write_text("placeholderReplacement=true")
        with self.assertRaises(ValueError):
            schema.validate(self.bundle)
        config.write_text("executeInTransaction=true")
        self.bundle["script_configs"].append(str(config))
        with self.assertRaises(ValueError):
            schema.validate(self.bundle)

    def test_main_success_lint_failure_and_bad_manifest(self):
        manifest = self.root / "manifest.json"
        manifest.write_text(json.dumps(self.bundle))
        argv = ["schema", "--manifest", str(manifest), "--config", str(self.config)]
        with patch.object(sys, "argv", argv):
            self.assertEqual(schema.main(), 0)
            self.sql.write_text("CREATE TABLE ( ;\n")
            self.assertEqual(schema.main(), 1)
            manifest.write_text("{}")
            self.assertEqual(schema.main(), 2)


if __name__ == "__main__":
    unittest.main()
