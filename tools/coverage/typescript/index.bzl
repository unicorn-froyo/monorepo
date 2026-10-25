"""Coverage for compiled TypeScript node:test suites."""

load("@npm//third_party/npm:c8/package_json.bzl", "bin")
load("//tools/coverage:config.bzl", "MINIMUM_LINE_COVERAGE")

def ts_coverage_test(name, entry_point = None, data = [], entry_points = []):
    """Run node:test suites under V8 coverage and save text and LCOV reports.

    Use entry_points for several suites; entry_point remains supported for
    existing callers. Node runs suites in separate processes.
    """
    if entry_point != None and entry_points:
        fail("Specify either entry_point or entry_points, not both")
    suites = [entry_point] if entry_point != None else entry_points
    if not suites:
        fail("ts_coverage_test requires at least one entry point")
    bin.c8_test(
        name = name,
        data = data,
        fixed_args = [
            "--reports-dir=\"$$TEST_UNDECLARED_OUTPUTS_DIR\"",
            "--temp-directory=\"$$TEST_TMPDIR/c8\"",
            "--check-coverage",
            "--lines=%s" % MINIMUM_LINE_COVERAGE,
            "--branches=0",
            "--functions=0",
            "--statements=0",
            "--reporter=text",
            "--reporter=lcovonly",
            "--include=src/apis/**/*.js",
            "--include=src/apis/**/*.ts",
            "--exclude=**/*.test.js",
            "--exclude=**/*.test.ts",
            "node",
            "--test",
        ] + suites,
        env = {"NODE_PATH": "third_party/npm/node_modules"},
    )
