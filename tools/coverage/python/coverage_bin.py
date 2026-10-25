"""Run declared unittest suites and preserve explicitly scoped coverage reports."""

import argparse
import json
import os
import shutil
import sys
import unittest
from pathlib import Path

from coverage import Coverage
from coverage.exceptions import CoverageException


def application_sources(candidates: list[str], tests: list[str]) -> list[str]:
    """Select workspace application files from a PyInfo source closure."""
    result = []
    for candidate in sorted(set(candidates)):
        path = Path(candidate)
        if (
            path.is_absolute()
            or ".." in path.parts
            or path.suffix != ".py"
            or candidate in tests
            or path.parts[0] == "tools"
            or "tests" in path.parts
            or path.name.startswith("test_")
            or path.name.endswith("_test.py")
        ):
            continue
        result.append(candidate)
    if not result:
        raise ValueError(
            "source_targets contains no workspace application Python sources"
        )
    return result


def write_reports(
    measurement: Coverage,
    sources: list[str],
    logical_paths: dict[str, str],
    output: Path,
    scratch: Path,
) -> float:
    """Save raw data and reports before the caller checks success or coverage."""
    data = measurement.get_data()
    # Initialize branch data even when none of the application was imported.
    # touch_files makes never-imported files visible in the saved database too.
    data.add_arcs({})
    data.touch_files(sources)
    measurement.save()
    shutil.copy2(scratch / ".coverage", output / ".coverage")
    lcov = output / "lcov.info"
    measurement.lcov_report(morfs=sources, outfile=str(lcov), ignore_errors=False)
    # coverage.py resolves runfile symlinks. Keep LCOV paths portable by mapping
    # its canonical source paths back to their declared workspace paths.
    records = []
    for line in lcov.read_text().splitlines():
        if line.startswith("SF:"):
            line = "SF:" + logical_paths[str(Path(line[3:]).resolve())]
        records.append(line)
    lcov.write_text("\n".join(records) + "\n")
    return measurement.report(morfs=sources, show_missing=True, ignore_errors=False)


def run(manifest_file: Path, config: Path, minimum: float) -> int:
    """Measure only declared application sources while running unittest suites."""
    manifest = json.loads(manifest_file.read_text())
    selected = application_sources(manifest["sources"], manifest["tests"])
    sources = [str(Path(source).resolve(strict=True)) for source in selected]
    output = Path(os.environ["TEST_UNDECLARED_OUTPUTS_DIR"])
    scratch = Path(os.environ["TEST_TMPDIR"]) / "python-coverage"
    output.mkdir(parents=True, exist_ok=True)
    scratch.mkdir(parents=True, exist_ok=True)
    runfiles = Path(os.environ.get("TEST_SRCDIR", Path.cwd().parent))
    sys.path[:0] = [str(Path.cwd())] + [
        str(runfiles / path) for path in manifest["imports"]
    ]

    measurement = Coverage(
        config_file=str(config),
        data_file=str(scratch / ".coverage"),
        branch=True,
        include=sources,
    )
    success = False
    measurement.start()
    try:
        program = unittest.main(
            module=None,
            argv=["unittest", *manifest["tests"]],
            verbosity=2,
            exit=False,
        )
        success = program.result.wasSuccessful() and program.result.testsRun > 0
    finally:
        measurement.stop()
        percentage = write_reports(
            measurement,
            sources,
            dict(zip(sources, selected, strict=True)),
            output,
            scratch,
        )
    print(f"Python line/branch coverage: {percentage:g}%; required: {minimum:g}%")
    return 0 if success and percentage >= minimum else 1


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--minimum", type=float, required=True)
    args = parser.parse_args()
    try:
        return run(args.manifest, args.config, args.minimum)
    except (CoverageException, OSError, ValueError, KeyError) as error:
        print(f"Python coverage failed: {error}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
