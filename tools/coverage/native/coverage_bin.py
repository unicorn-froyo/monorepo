"""Run instrumented Go/Rust tests and preserve coverage in Bazel test outputs."""

import json
import os
import re
import subprocess
import sys
from pathlib import Path


def go_report(profile: Path, module: str = "") -> str:
    """Convert Go's block profile to line-based LCOV."""
    files: dict[str, dict[int, int]] = {}
    for record in profile.read_text().splitlines()[1:]:
        match = re.fullmatch(r"(.+):(\d+)\.\d+,(\d+)\.(\d+) \d+ (\d+)", record)
        if not match:
            raise ValueError(f"Invalid Go coverage record: {record}")
        filename, start, end, end_column, count = match.groups()
        if module:
            filename = filename.removeprefix(module + "/")
        # Go's end position is exclusive; column 1 belongs to the next line.
        last = int(end) - (int(end_column) == 1)
        lines = files.setdefault(filename, {})
        for line in range(int(start), last + 1):
            lines[line] = max(lines.get(line, 0), int(count))
    records = []
    for filename, lines in sorted(files.items()):
        records += [f"SF:{filename}"]
        records += [f"DA:{line},{count}" for line, count in sorted(lines.items())]
        records += [
            f"LF:{len(lines)}",
            f"LH:{sum(count > 0 for count in lines.values())}",
            "end_of_record",
        ]
    return "\n".join(records) + "\n"


def enforce_threshold(report: str, minimum: float) -> None:
    """Enforce aggregate line coverage without rounding up near the boundary."""
    found = sum(int(line[3:]) for line in report.splitlines() if line.startswith("LF:"))
    hit = sum(int(line[3:]) for line in report.splitlines() if line.startswith("LH:"))
    if found <= 0 or hit < 0 or hit > found:
        raise RuntimeError("Coverage report has invalid or empty line totals")
    percentage = 100 * hit / found
    print(f"Line coverage: {hit}/{found} ({percentage:.2f}%); required: {minimum:g}%")
    if hit * 100 < minimum * found:
        raise RuntimeError(f"Line coverage {percentage:.2f}% is below {minimum:g}%")


def main() -> None:
    language, binary, encoded_env, minimum, *tools = sys.argv[1:]
    binary = str(Path(binary).absolute())
    output = Path(os.environ["TEST_UNDECLARED_OUTPUTS_DIR"])
    output.mkdir(parents=True, exist_ok=True)
    scratch = Path(os.environ["TEST_TMPDIR"]) / "native-coverage"
    scratch.mkdir(parents=True, exist_ok=True)
    env = os.environ.copy()
    env.update(json.loads(encoded_env))
    # This runner owns collection, including when invoked by `bazel coverage`.
    env.pop("COVERAGE_OUTPUT_FILE", None)
    if language == "go":
        profile = output / "coverage.out"
        subprocess.run([binary, f"-test.coverprofile={profile}"], env=env, check=True)
        module = Path("third_party/golang/go.mod").read_text().splitlines()[0].split()[1]
        report = go_report(profile, module)
    else:
        llvm_cov, llvm_profdata = [str(Path(tool).absolute()) for tool in tools]
        env["LLVM_PROFILE_FILE"] = str(scratch / "%p-%m.profraw")
        subprocess.run([binary], env=env, check=True)
        profiles = sorted(scratch.glob("*.profraw"))
        if not profiles:
            raise RuntimeError("Rust test produced no coverage profiles")
        merged = scratch / "coverage.profdata"
        subprocess.run(
            [llvm_profdata, "merge", "-sparse", *map(str, profiles), "-o", str(merged)], check=True
        )
        report = subprocess.check_output(
            [
                llvm_cov,
                "export",
                "--format=lcov",
                binary,
                f"--instr-profile={merged}",
                "--ignore-filename-regex=_test[.]rs$",
            ],
            text=True,
        )
    # Reject empty reports rather than passing a silently uninstrumented test.
    if not any("src/apis/" in line for line in report.splitlines() if line.startswith("SF:")):
        raise RuntimeError("Coverage report contains no API source files")
    (output / "lcov.info").write_text(report)
    print(f"{language} LCOV coverage saved to {output / 'lcov.info'}")
    enforce_threshold(report, float(minimum))


if __name__ == "__main__":
    main()
