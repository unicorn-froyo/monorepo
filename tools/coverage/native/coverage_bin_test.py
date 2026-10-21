"""Tests for conversion of Go block profiles to LCOV."""

import tempfile
import unittest
from pathlib import Path

from tools.coverage.native.coverage_bin import enforce_threshold, go_report


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
        report = self.report(
            "src/apis/example.go:3.1,4.5 1 2\n"
            "src/apis/example.go:4.6,5.5 1 0\n"
        )
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


if __name__ == "__main__":
    unittest.main()
