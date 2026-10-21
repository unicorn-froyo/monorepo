"""Rust coverage using rules_rust's LLVM instrumentation."""

def rs_coverage_test(name, tests):
    """Group Rust tests for `bazelisk coverage`; no second test binary is needed."""
    native.test_suite(name = name, tests = tests)
