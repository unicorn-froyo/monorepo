"""Exercise formatting and type-check rejection with real pinned tools."""

import argparse
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


class QualityChecksTest(unittest.TestCase):
    ruff = Path()
    pyright = Path()
    runner = Path()
    ruff_config = Path()
    pyright_config = Path()

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
    parser = argparse.ArgumentParser()
    for option in ("ruff", "pyright", "runner", "ruff_config", "pyright_config"):
        parser.add_argument("--" + option, required=True, type=Path)
    args, remaining = parser.parse_known_args()
    for option, value in vars(args).items():
        setattr(QualityChecksTest, option, value.absolute())
    unittest.main(argv=[sys.argv[0], *remaining])
