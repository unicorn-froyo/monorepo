"""Coverage for compiled TypeScript node:test suites."""

load("@npm//third_party/npm:c8/package_json.bzl", "bin")

def ts_coverage_test(name, entry_point, data):
    """Run a suite under V8 coverage and save text and LCOV reports."""
    bin.c8_test(
        name = name,
        data = data,
        fixed_args = [
            "--reports-dir=\"$$TEST_UNDECLARED_OUTPUTS_DIR\"",
            "--temp-directory=\"$$TEST_TMPDIR/c8\"",
            "--reporter=text",
            "--reporter=lcovonly",
            "--include=src/apis/**/*.js",
            "--include=src/apis/**/*.ts",
            "--exclude=**/*.test.js",
            "--exclude=**/*.test.ts",
            "node",
            entry_point,
        ],
        env = {"NODE_PATH": "third_party/npm/node_modules"},
    )
