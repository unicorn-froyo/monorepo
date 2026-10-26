"""Exercise formatting and type-check rejection with real pinned tools."""

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

from tools.lint.python import format_bin, ruff_bin, typecheck_bin


class QualityChecksTest(unittest.TestCase):
    ruff = Path()
    formatter = Path()
    pyright = Path()
    runner = Path()
    ruff_config = Path()
    pyright_config = Path()

    @classmethod
    def setUpClass(cls) -> None:
        runfiles = Path(os.environ["TEST_SRCDIR"])
        workspace = runfiles / os.environ.get("TEST_WORKSPACE", "_main")
        package = workspace / "tools/lint/python"
        cls.ruff = package / "ruff_bin"
        cls.formatter = package / "py_format_bin"
        cls.pyright = package / "pyright_bin_/pyright_bin"
        cls.runner = package / "typecheck_bin"
        cls.ruff_config = package / "ruff.toml"
        cls.pyright_config = package / "pyrightconfig.json"

    def format_source(self, source: str) -> subprocess.CompletedProcess[str]:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "example.py"
            path.write_text(source)
            return subprocess.run(
                [str(self.ruff), "format", "--check", "--config", str(self.ruff_config), str(path)],
                capture_output=True,
                text=True,
                check=False,
            )

    def typecheck_source(self, source: str) -> subprocess.CompletedProcess[str]:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "example.py"
            path.write_text(source)
            return subprocess.run(
                [
                    str(self.runner),
                    "--pyright",
                    str(self.pyright),
                    "--config",
                    str(self.pyright_config),
                    str(path),
                ],
                capture_output=True,
                text=True,
                check=False,
            )

    def test_formatter_rejects_bad_layout(self) -> None:
        result = self.format_source("answer=42\n")
        self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
        self.assertIn("Would reformat", result.stdout + result.stderr)

    def test_formatter_accepts_formatted_source(self) -> None:
        result = self.format_source("answer = 42\n")
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_runnable_formatter_rewrites_source(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "example.py"
            path.write_text("answer=42\n")
            result = subprocess.run(
                [str(self.formatter), str(path)],
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertEqual(path.read_text(), "answer = 42\n")

    def test_formatter_entrypoint_resolves_workspace_paths(self) -> None:
        with (
            patch.dict("os.environ", {"BUILD_WORKSPACE_DIRECTORY": "/workspace"}),
            patch.object(sys, "argv", ["format_bin", "example.py", "/absolute.py"]),
            patch.object(format_bin.os, "execv") as execute,
        ):
            format_bin.main()

        arguments = execute.call_args.args[1]
        self.assertEqual(
            arguments[0:4], ["ruff", "format", "--config", "/workspace/tools/lint/python/ruff.toml"]
        )
        self.assertEqual(arguments[-2:], ["/workspace/example.py", "/absolute.py"])

    def test_typecheck_entrypoint_uses_declared_runfiles(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            config = root / "pyrightconfig.json"
            source = root / "example.py"
            config.write_text('{"typeCheckingMode": "standard"}')
            source.write_text("answer: int = 42\n")
            completed = Mock(returncode=7)
            captured = {}

            def run_typecheck(command, *, env, check):
                captured["command"] = command
                captured["config"] = json.loads(Path(command[4]).read_text())
                captured["env"] = env
                captured["check"] = check
                return completed

            with (
                patch.dict(
                    "os.environ",
                    {
                        "RUNFILES_DIR": str(root),
                        "TEST_WORKSPACE": "_main",
                        "TEST_TMPDIR": str(root),
                        "PYTHONPATH": "ambient",
                    },
                ),
                patch.object(
                    sys,
                    "argv",
                    [
                        "typecheck_bin",
                        "--pyright",
                        "pyright",
                        "--config",
                        str(config),
                        "--imports-json",
                        '["dependency"]',
                        str(source),
                    ],
                ),
                patch.object(typecheck_bin.subprocess, "run", side_effect=run_typecheck),
            ):
                self.assertEqual(typecheck_bin.main(), 7)

            self.assertEqual(
                captured["config"]["extraPaths"],
                [str(root / "_main"), str(root / "dependency")],
            )
            self.assertNotIn("PYTHONPATH", captured["env"])
            self.assertFalse(captured["check"])

    def test_ruff_entrypoint_is_importable(self) -> None:
        self.assertTrue(Path(ruff_bin.ruff.__file__).is_file())

    def test_pyright_rejects_incompatible_assignment(self) -> None:
        result = self.typecheck_source('answer: int = "incorrect"\n')
        self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
        self.assertIn("reportAssignmentType", result.stdout + result.stderr)

    def test_pyright_accepts_valid_annotation(self) -> None:
        result = self.typecheck_source("answer: int = 42\n")
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_pyright_rejects_undeclared_import(self) -> None:
        result = self.typecheck_source("import dependency_not_declared_for_quality_test\n")
        self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
        self.assertIn("reportMissingImports", result.stdout + result.stderr)


if __name__ == "__main__":
    unittest.main()
