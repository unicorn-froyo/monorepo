"""Regression tests for explicit source coverage and durable failure reports."""

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

from coverage import CoverageData

from tools.coverage.python import coverage_bin


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
        manifest.write_text(json.dumps({"sources": sources, "tests": tests, "imports": []}))
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

    def test_source_scope_accepts_tooling_sources_and_omits_test_files(self):
        self.assertEqual(
            coverage_bin.application_sources(
                [
                    "tools/coverage/python/coverage_bin.py",
                    "tools/coverage/python/coverage_bin_test.py",
                    "tools/coverage/python/tests/helper.py",
                    "../external/site-packages/coverage/__init__.py",
                ],
                [],
            ),
            ["tools/coverage/python/coverage_bin.py"],
        )
        with self.assertRaisesRegex(ValueError, "no workspace application Python sources"):
            coverage_bin.application_sources(["app_test.py"], ["app_test.py"])

    def test_write_reports_saves_raw_data_and_rewrites_lcov_paths(self):
        source = self.root / "app.py"
        self.write("app.py", "VALUE = 1\n")
        self.output.mkdir()
        self.scratch.mkdir()
        (self.scratch / ".coverage").write_text("raw coverage")
        measurement = Mock()
        data = measurement.get_data.return_value

        def write_lcov(*, outfile, **_kwargs):
            Path(outfile).write_text(f"SF:{source}\nDA:1,1\nend_of_record\n")

        measurement.lcov_report.side_effect = write_lcov
        measurement.report.return_value = 100.0

        percentage = coverage_bin.write_reports(
            measurement,
            [str(source)],
            {str(source): "app.py"},
            self.output,
            self.scratch,
        )

        self.assertEqual(percentage, 100.0)
        self.assertEqual((self.output / ".coverage").read_text(), "raw coverage")
        self.assertEqual(
            (self.output / "lcov.info").read_text(),
            "SF:app.py\nDA:1,1\nend_of_record\n",
        )
        data.add_arcs.assert_called_once_with({})
        data.touch_files.assert_called_once_with([str(source)])
        measurement.save.assert_called_once_with()

    def test_run_enforces_test_success_and_threshold(self):
        self.write("app.py", "VALUE = 1\n")
        self.write("app_test.py", "")
        manifest = self.root / "manifest.json"
        manifest.write_text(
            json.dumps({"sources": ["app.py"], "tests": ["app_test.py"], "imports": []})
        )
        measurement = Mock()
        program = Mock()
        program.result.testsRun = 1
        old_cwd = Path.cwd()
        self.addCleanup(os.chdir, old_cwd)
        os.chdir(self.root)

        with (
            patch.dict(
                os.environ,
                {
                    "TEST_UNDECLARED_OUTPUTS_DIR": str(self.output),
                    "TEST_TMPDIR": str(self.scratch),
                },
            ),
            patch.object(coverage_bin, "Coverage", return_value=measurement),
            patch.object(coverage_bin.unittest, "main", return_value=program),
            patch.object(coverage_bin, "write_reports", return_value=100.0),
        ):
            program.result.wasSuccessful.return_value = True
            self.assertEqual(coverage_bin.run(manifest, self.config, 100), 0)
            program.result.wasSuccessful.return_value = False
            self.assertEqual(coverage_bin.run(manifest, self.config, 100), 1)

        self.assertEqual(measurement.start.call_count, 2)
        self.assertEqual(measurement.stop.call_count, 2)

    def test_main_returns_runner_status_and_reports_expected_errors(self):
        with (
            patch.object(
                sys,
                "argv",
                ["coverage_bin", "--manifest", "manifest", "--config", "config", "--minimum", "90"],
            ),
            patch.object(coverage_bin, "run", return_value=1) as run,
        ):
            self.assertEqual(coverage_bin.main(), 1)
            run.assert_called_once_with(Path("manifest"), Path("config"), 90.0)

        with (
            patch.object(
                sys,
                "argv",
                ["coverage_bin", "--manifest", "manifest", "--config", "config", "--minimum", "90"],
            ),
            patch.object(coverage_bin, "run", side_effect=ValueError("bad manifest")),
            patch("sys.stderr"),
        ):
            self.assertEqual(coverage_bin.main(), 2)

    def test_never_imported_source_counts_as_uncovered(self):
        self.write("app.py", "VALUE = 1\n")
        self.write("unused.py", "UNUSED = 2\n")
        self.write(
            "app_test.py",
            "import app\nimport unittest\nclass Check(unittest.TestCase):\n def test_value(self): self.assertEqual(app.VALUE, 1)\n",
        )
        result = self.run_project(["app.py", "unused.py"], ["app_test.py"])
        self.assertEqual(result.returncode, 1, result.stdout)
        report = self.assert_reports(["app.py", "unused.py"])
        self.assertIn("SF:unused.py\n", report)
        self.assertIn("DA:1,0", report)

    def test_no_application_imports_still_produce_zero_coverage(self):
        self.write("unused.py", "VALUE = 1\n")
        self.write(
            "empty_test.py",
            "import unittest\nclass Check(unittest.TestCase):\n def test_ok(self): self.assertTrue(True)\n",
        )
        result = self.run_project(["unused.py"], ["empty_test.py"])
        self.assertEqual(result.returncode, 1, result.stdout)
        self.assertIn("LH:0", self.assert_reports(["unused.py"]))

    def test_multiple_suites_runtime_data_and_exclusions(self):
        self.write(
            "app.py",
            "from pathlib import Path\ndef first():\n return Path('payload.txt').read_text()\ndef second():\n return 'second'\n",
        )
        self.write("payload.txt", "runtime data")
        self.write(
            "first_test.py",
            "import app\nimport unittest\nclass First(unittest.TestCase):\n def test_first(self): self.assertEqual(app.first(), 'runtime data')\n",
        )
        self.write(
            "second_test.py",
            "import app\nimport unittest\nclass Second(unittest.TestCase):\n def test_second(self): self.assertEqual(app.second(), 'second')\n",
        )
        # Invalid excluded files must not be parsed, measured, or reported.
        for name in [
            "tests/helper_test.py",
            "unused_test.py",
            "extra_test.py",
        ]:
            self.write(name, "invalid python !!!!")
        result = self.run_project(
            [
                "app.py",
                "first_test.py",
                "second_test.py",
                "tests/helper_test.py",
                "unused_test.py",
                "extra_test.py",
                "../external/vendor.py",
            ],
            ["first_test.py", "second_test.py"],
        )
        self.assertEqual(result.returncode, 0, result.stdout)
        self.assert_reports(["app.py"])
        self.assertIn("Ran 2 tests", result.stdout)

    def test_explicit_tool_source_is_measured(self):
        self.write("tools/helper.py", "def value():\n return 42\n")
        self.write(
            "helper_test.py",
            "from tools import helper\nimport unittest\nclass Check(unittest.TestCase):\n def test_value(self): self.assertEqual(helper.value(), 42)\n",
        )
        result = self.run_project(["tools/helper.py"], ["helper_test.py"])
        self.assertEqual(result.returncode, 0, result.stdout)
        self.assert_reports(["tools/helper.py"])

    def test_branch_gap_fails_even_when_all_lines_execute(self):
        self.write("app.py", "def choose(flag):\n if flag:\n  result = 1\n return 1\n")
        self.write(
            "app_test.py",
            "import app\nimport unittest\nclass Check(unittest.TestCase):\n def test_true(self): self.assertEqual(app.choose(True), 1)\n",
        )
        result = self.run_project(["app.py"], ["app_test.py"])
        self.assertEqual(result.returncode, 1, result.stdout)
        report = self.assert_reports(["app.py"])
        self.assertIn("LF:4\nLH:4", report)
        self.assertIn("BRF:2\nBRH:1", report)

    def test_failing_test_preserves_reports(self):
        self.write("app.py", "VALUE = 1\n")
        self.write(
            "app_test.py",
            "import app\nimport unittest\nclass Check(unittest.TestCase):\n def test_wrong(self): self.assertEqual(app.VALUE, 2)\n",
        )
        result = self.run_project(["app.py"], ["app_test.py"])
        self.assertEqual(result.returncode, 1, result.stdout)
        self.assert_reports(["app.py"])
        self.assertIn("FAILED (failures=1)", result.stdout)

    def test_invalid_application_source_fails_analysis(self):
        self.write("broken.py", "def broken(:\n")
        self.write(
            "empty_test.py",
            "import unittest\nclass Check(unittest.TestCase):\n def test_ok(self): self.assertTrue(True)\n",
        )
        result = self.run_project(["broken.py"], ["empty_test.py"])
        self.assertEqual(result.returncode, 2, result.stdout)
        self.assertIn("Python coverage failed", result.stdout)
        self.assertIn("parse", result.stdout.lower())
        self.assertTrue((self.output / ".coverage").is_file())

    def test_empty_application_scope_is_rejected(self):
        result = self.run_project(
            ["tests/helper_test.py", "empty_test.py", "../external/vendor.py"],
            ["app_test.py"],
        )
        self.assertEqual(result.returncode, 2, result.stdout)
        self.assertIn("no workspace application Python sources", result.stdout)


if __name__ == "__main__":
    unittest.main()
