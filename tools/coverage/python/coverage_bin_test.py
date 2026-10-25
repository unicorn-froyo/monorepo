"""Regression tests for explicit source coverage and durable failure reports."""

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from coverage import CoverageData


class CoverageRunnerTest(unittest.TestCase):
    """Exercise the real runner in fresh interpreters and temporary projects."""

    def setUp(self):
        self.project = tempfile.TemporaryDirectory()
        self.addCleanup(self.project.cleanup)
        self.root = Path(self.project.name).resolve()
        self.output = self.root / "reports"
        self.scratch = self.root / "scratch"
        self.runner = Path("tools/coverage/python/coverage_bin.py").resolve()
        self.config = Path("tools/coverage/python/.coveragerc").resolve()

    def write(self, name, content):
        path = self.root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content)

    def run_project(self, sources, tests, minimum=100):
        manifest = self.root / "manifest.json"
        manifest.write_text(
            json.dumps({"sources": sources, "tests": tests, "imports": []})
        )
        env = os.environ.copy()
        env.update(
            {
                "TEST_UNDECLARED_OUTPUTS_DIR": str(self.output),
                "TEST_TMPDIR": str(self.scratch),
                # A plain interpreter needs the pinned coverage package from the
                # py_test's runfiles, without inheriting an ambient virtualenv.
                "PYTHONPATH": os.pathsep.join(sys.path),
            }
        )
        return subprocess.run(
            [
                sys.executable,
                str(self.runner),
                "--manifest",
                str(manifest),
                "--config",
                str(self.config),
                "--minimum",
                str(minimum),
            ],
            cwd=self.root,
            env=env,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            check=False,
        )

    def assert_reports(self, expected_sources):
        report = (self.output / "lcov.info").read_text()
        self.assertEqual(
            {line[3:] for line in report.splitlines() if line.startswith("SF:")},
            set(expected_sources),
        )
        data = CoverageData(basename=str(self.output / ".coverage"))
        data.read()
        self.assertEqual(
            {
                Path(filename).relative_to(self.root).as_posix()
                for filename in data.measured_files()
            },
            set(expected_sources),
        )
        self.assertTrue(data.has_arcs())
        return report

    def test_never_imported_source_counts_as_uncovered(self):
        self.write("app.py", "VALUE = 1\n")
        self.write("unused.py", "UNUSED = 2\n")
        self.write(
            "test_app.py",
            "import app\nimport unittest\nclass Check(unittest.TestCase):\n def test_value(self): self.assertEqual(app.VALUE, 1)\n",
        )
        result = self.run_project(["app.py", "unused.py"], ["test_app.py"])
        self.assertEqual(result.returncode, 1, result.stdout)
        report = self.assert_reports(["app.py", "unused.py"])
        self.assertIn("SF:unused.py\n", report)
        self.assertIn("DA:1,0", report)

    def test_no_application_imports_still_produce_zero_coverage(self):
        self.write("unused.py", "VALUE = 1\n")
        self.write(
            "test_empty.py",
            "import unittest\nclass Check(unittest.TestCase):\n def test_ok(self): self.assertTrue(True)\n",
        )
        result = self.run_project(["unused.py"], ["test_empty.py"])
        self.assertEqual(result.returncode, 1, result.stdout)
        self.assertIn("LH:0", self.assert_reports(["unused.py"]))

    def test_multiple_suites_runtime_data_and_exclusions(self):
        self.write(
            "app.py",
            "from pathlib import Path\ndef first():\n return Path('payload.txt').read_text()\ndef second():\n return 'second'\n",
        )
        self.write("payload.txt", "runtime data")
        self.write(
            "test_first.py",
            "import app\nimport unittest\nclass First(unittest.TestCase):\n def test_first(self): self.assertEqual(app.first(), 'runtime data')\n",
        )
        self.write(
            "test_second.py",
            "import app\nimport unittest\nclass Second(unittest.TestCase):\n def test_second(self): self.assertEqual(app.second(), 'second')\n",
        )
        # Invalid excluded files must not be parsed, measured, or reported.
        for name in [
            "tools/helper.py",
            "tests/helper.py",
            "test_unused.py",
            "extra_test.py",
        ]:
            self.write(name, "invalid python !!!!")
        result = self.run_project(
            [
                "app.py",
                "test_first.py",
                "test_second.py",
                "tools/helper.py",
                "tests/helper.py",
                "test_unused.py",
                "extra_test.py",
                "../external/vendor.py",
            ],
            ["test_first.py", "test_second.py"],
        )
        self.assertEqual(result.returncode, 0, result.stdout)
        self.assert_reports(["app.py"])
        self.assertIn("Ran 2 tests", result.stdout)

    def test_branch_gap_fails_even_when_all_lines_execute(self):
        self.write("app.py", "def choose(flag):\n if flag:\n  result = 1\n return 1\n")
        self.write(
            "test_app.py",
            "import app\nimport unittest\nclass Check(unittest.TestCase):\n def test_true(self): self.assertEqual(app.choose(True), 1)\n",
        )
        result = self.run_project(["app.py"], ["test_app.py"])
        self.assertEqual(result.returncode, 1, result.stdout)
        report = self.assert_reports(["app.py"])
        self.assertIn("LF:4\nLH:4", report)
        self.assertIn("BRF:2\nBRH:1", report)

    def test_failing_test_preserves_reports(self):
        self.write("app.py", "VALUE = 1\n")
        self.write(
            "test_app.py",
            "import app\nimport unittest\nclass Check(unittest.TestCase):\n def test_wrong(self): self.assertEqual(app.VALUE, 2)\n",
        )
        result = self.run_project(["app.py"], ["test_app.py"])
        self.assertEqual(result.returncode, 1, result.stdout)
        self.assert_reports(["app.py"])
        self.assertIn("FAILED (failures=1)", result.stdout)

    def test_invalid_application_source_fails_analysis(self):
        self.write("broken.py", "def broken(:\n")
        self.write(
            "test_empty.py",
            "import unittest\nclass Check(unittest.TestCase):\n def test_ok(self): self.assertTrue(True)\n",
        )
        result = self.run_project(["broken.py"], ["test_empty.py"])
        self.assertEqual(result.returncode, 2, result.stdout)
        self.assertIn("Python coverage failed", result.stdout)
        self.assertIn("parse", result.stdout.lower())
        self.assertTrue((self.output / ".coverage").is_file())

    def test_empty_application_scope_is_rejected(self):
        result = self.run_project(["tools/helper.py"], ["test_app.py"])
        self.assertEqual(result.returncode, 2, result.stdout)
        self.assertIn("no workspace application Python sources", result.stdout)


if __name__ == "__main__":
    unittest.main()
