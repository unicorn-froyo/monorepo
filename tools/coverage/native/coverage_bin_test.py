"""Tests for conversion of Go block profiles to LCOV."""

import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from tools.coverage.native import coverage_bin
from tools.coverage.native.coverage_bin import enforce_threshold, go_report, validate_sources


class GoReportTest(unittest.TestCase):
    def report(self, records: str, module: str = "") -> str:
        with tempfile.TemporaryDirectory() as directory:
            profile = Path(directory) / "coverage.out"
            profile.write_text("mode: atomic\n" + records)
            return go_report(profile, module)

    def test_counts_lines_and_excludes_exclusive_end(self):
        report = self.report("src/apis/example.go:3.1,6.1 3 2\n")
        self.assertIn("DA:3,2\nDA:4,2\nDA:5,2\nLF:3\nLH:3\n", report)
        self.assertNotIn("DA:6,", report)

    def test_overlapping_blocks_keep_covered_line(self):
        report = self.report("src/apis/example.go:3.1,4.5 1 2\nsrc/apis/example.go:4.6,5.5 1 0\n")
        self.assertIn("DA:4,2\nDA:5,0\nLF:3\nLH:2\n", report)

    def test_multiple_files_have_separate_records(self):
        report = self.report("src/apis/b.go:1.1,1.5 1 1\nsrc/apis/a.go:2.1,2.5 1 0\n")
        self.assertEqual(report.count("end_of_record"), 2)
        self.assertTrue(report.startswith("SF:src/apis/a.go\n"))

    def test_module_paths_become_workspace_relative(self):
        report = self.report("example.org/repo/src/apis/a.go:1.1,1.5 1 1\n", "example.org/repo")
        self.assertTrue(report.startswith("SF:src/apis/a.go\n"))

    def test_malformed_profile_fails(self):
        with self.assertRaises(ValueError):
            self.report("not a coverage record\n")


class ThresholdTest(unittest.TestCase):
    def test_full_coverage_passes(self):
        enforce_threshold("LF:10\nLH:10\n", 100)

    def test_single_uncovered_line_fails_at_100(self):
        with self.assertRaisesRegex(RuntimeError, "below 100%"):
            enforce_threshold("LF:10000\nLH:9999\n", 100)

    def test_exact_boundary_passes(self):
        enforce_threshold("LF:10\nLH:8\n", 80)

    def test_below_boundary_fails(self):
        with self.assertRaisesRegex(RuntimeError, "below 80%"):
            enforce_threshold("LF:10001\nLH:8000\n", 80)

    def test_aggregate_across_files(self):
        enforce_threshold("LF:2\nLH:0\nLF:8\nLH:8\n", 80)

    def test_empty_report_fails(self):
        with self.assertRaisesRegex(RuntimeError, "empty line totals"):
            enforce_threshold("LF:0\nLH:0\n", 80)

    def test_invalid_totals_fail(self):
        with self.assertRaisesRegex(RuntimeError, "invalid"):
            enforce_threshold("LF:10\nLH:11\n", 80)


class SourceValidationTest(unittest.TestCase):
    def test_accepts_workspace_relative_application_source(self):
        validate_sources("SF:tools/example/main.go\nLF:1\nLH:1\n", "tools/example/")

    def test_rejects_report_without_sources(self):
        with self.assertRaisesRegex(RuntimeError, "no source files"):
            validate_sources("LF:0\nLH:0\n", "tools/example/")

    def test_rejects_source_outside_target_package(self):
        with self.assertRaisesRegex(RuntimeError, "no sources under tools/example/"):
            validate_sources("SF:src/apis/example.go\n", "tools/example/")

    def test_rejects_absolute_source(self):
        with self.assertRaisesRegex(RuntimeError, "non-portable"):
            validate_sources("SF:/sandbox/tools/example/main.go\n", "tools/example/")

    def test_rejects_test_source(self):
        with self.assertRaisesRegex(RuntimeError, "test sources"):
            validate_sources("SF:tools/example/main_test.go\n", "tools/example/")


class RunnerTest(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.output = self.root / "output"
        self.scratch = self.root / "scratch"
        self.environment = {
            "TEST_UNDECLARED_OUTPUTS_DIR": str(self.output),
            "TEST_TMPDIR": str(self.scratch),
            "COVERAGE_OUTPUT_FILE": "ambient",
        }

    def test_go_runner_writes_and_enforces_lcov(self):
        report = "SF:src/apis/example.go\nDA:1,1\nLF:1\nLH:1\nend_of_record\n"
        with (
            patch.dict(os.environ, self.environment, clear=True),
            patch.object(
                sys,
                "argv",
                ["coverage_bin", "go", "test-bin", "{}", "100", "src/apis/"],
            ),
            patch.object(
                coverage_bin.subprocess,
                "run",
                return_value=coverage_bin.subprocess.CompletedProcess([], 0),
            ) as run,
            patch.object(coverage_bin, "go_report", return_value=report) as convert,
            patch.object(coverage_bin, "enforce_threshold") as enforce,
            patch.object(Path, "exists", return_value=True),
            patch.object(Path, "read_text", return_value="module example.org/repo\n"),
        ):
            coverage_bin.main()

        self.assertEqual((self.output / "lcov.info").read_text(), report)
        self.assertNotIn("COVERAGE_OUTPUT_FILE", run.call_args.kwargs["env"])
        convert.assert_called_once()
        enforce.assert_called_once_with(report, 100.0)

    def test_rust_runner_merges_profiles_and_exports_lcov(self):
        report = "SF:src/apis/example.rs\nDA:1,1\nLF:1\nLH:1\nend_of_record\n"

        def run_binary(*_args, **_kwargs):
            profile_dir = self.scratch / "native-coverage"
            profile_dir.mkdir(parents=True, exist_ok=True)
            (profile_dir / "test.profraw").write_text("profile")

        with (
            patch.dict(os.environ, self.environment, clear=True),
            patch.object(
                sys,
                "argv",
                [
                    "coverage_bin",
                    "rust",
                    "test-bin",
                    "{}",
                    "100",
                    "src/apis/",
                    "llvm-cov",
                    "llvm-profdata",
                ],
            ),
            patch.object(coverage_bin.subprocess, "run", side_effect=run_binary) as run,
            patch.object(coverage_bin.subprocess, "check_output", return_value=report) as export,
            patch.object(coverage_bin, "enforce_threshold") as enforce,
        ):
            coverage_bin.main()

        self.assertGreaterEqual(run.call_count, 2)
        export.assert_called_once()
        enforce.assert_called_once_with(report, 100.0)

    def test_rust_runner_rejects_missing_profiles(self):
        with (
            patch.dict(os.environ, self.environment, clear=True),
            patch.object(
                sys,
                "argv",
                [
                    "coverage_bin",
                    "rust",
                    "test-bin",
                    "{}",
                    "100",
                    "src/apis/",
                    "llvm-cov",
                    "llvm-profdata",
                ],
            ),
            patch.object(coverage_bin.subprocess, "run"),
            self.assertRaisesRegex(RuntimeError, "no coverage profiles"),
        ):
            coverage_bin.main()

    def test_runner_rejects_report_without_api_sources(self):
        with (
            patch.dict(os.environ, self.environment, clear=True),
            patch.object(
                sys,
                "argv",
                ["coverage_bin", "go", "test-bin", "{}", "100", "src/apis/"],
            ),
            patch.object(
                coverage_bin.subprocess,
                "run",
                return_value=coverage_bin.subprocess.CompletedProcess([], 0),
            ),
            patch.object(coverage_bin, "go_report", return_value="SF:vendor/example.go\n"),
            patch.object(Path, "exists", return_value=True),
            patch.object(Path, "read_text", return_value="module example.org/repo\n"),
            self.assertRaisesRegex(RuntimeError, "no sources under src/apis/"),
        ):
            coverage_bin.main()

    def test_go_runner_preserves_lcov_before_propagating_test_failure(self):
        report = "SF:src/apis/example.go\nDA:1,1\nLF:1\nLH:1\nend_of_record\n"
        with (
            patch.dict(os.environ, self.environment, clear=True),
            patch.object(
                sys,
                "argv",
                ["coverage_bin", "go", "test-bin", "{}", "100", "src/apis/"],
            ),
            patch.object(
                coverage_bin.subprocess,
                "run",
                return_value=coverage_bin.subprocess.CompletedProcess(["test-bin"], 1),
            ),
            patch.object(Path, "exists", return_value=True),
            patch.object(Path, "read_text", return_value="module example.org/repo\n"),
            patch.object(coverage_bin, "go_report", return_value=report),
            self.assertRaises(coverage_bin.subprocess.CalledProcessError),
        ):
            coverage_bin.main()

        self.assertEqual((self.output / "lcov.info").read_text(), report)

    def test_go_runner_preserves_lcov_on_threshold_failure(self):
        report = "SF:src/apis/example.go\nDA:1,0\nLF:1\nLH:0\nend_of_record\n"
        with (
            patch.dict(os.environ, self.environment, clear=True),
            patch.object(
                sys,
                "argv",
                ["coverage_bin", "go", "test-bin", "{}", "100", "src/apis/"],
            ),
            patch.object(
                coverage_bin.subprocess,
                "run",
                return_value=coverage_bin.subprocess.CompletedProcess(["test-bin"], 0),
            ),
            patch.object(Path, "exists", return_value=True),
            patch.object(Path, "read_text", return_value="module example.org/repo\n"),
            patch.object(coverage_bin, "go_report", return_value=report),
            self.assertRaisesRegex(RuntimeError, "below 100%"),
        ):
            coverage_bin.main()

        self.assertEqual((self.output / "lcov.info").read_text(), report)

    def test_go_runner_propagates_failure_without_profile(self):
        with (
            patch.dict(os.environ, self.environment, clear=True),
            patch.object(
                sys,
                "argv",
                ["coverage_bin", "go", "test-bin", "{}", "100", "src/apis/"],
            ),
            patch.object(
                coverage_bin.subprocess,
                "run",
                return_value=coverage_bin.subprocess.CompletedProcess(["test-bin"], 1),
            ),
            patch.object(Path, "exists", return_value=False),
            self.assertRaises(coverage_bin.subprocess.CalledProcessError),
        ):
            coverage_bin.main()

    def test_go_runner_rejects_missing_profile_after_success(self):
        with (
            patch.dict(os.environ, self.environment, clear=True),
            patch.object(
                sys,
                "argv",
                ["coverage_bin", "go", "test-bin", "{}", "100", "src/apis/"],
            ),
            patch.object(
                coverage_bin.subprocess,
                "run",
                return_value=coverage_bin.subprocess.CompletedProcess(["test-bin"], 0),
            ),
            patch.object(Path, "exists", return_value=False),
            self.assertRaisesRegex(RuntimeError, "no coverage profile"),
        ):
            coverage_bin.main()


if __name__ == "__main__":
    unittest.main()
