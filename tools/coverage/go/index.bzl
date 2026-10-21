"""Go coverage using rules_go's native Bazel instrumentation."""

def go_coverage_test(name, tests):
    """Group Go tests for `bazelisk coverage`; no second test binary is needed."""
    native.test_suite(name = name, tests = tests)
