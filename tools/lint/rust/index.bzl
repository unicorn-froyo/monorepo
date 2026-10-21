"""Rust lint tests backed by Clippy and rustfmt."""

load("@rules_rust//rust:defs.bzl", "rust_clippy_test", "rustfmt_test")

def rs_lint_test(name, targets):
    """Check Rust targets for lint findings and formatting errors."""
    rust_clippy_test(
        name = name + "_clippy_test",
        targets = targets,
    )
    rustfmt_test(
        name = name + "_format_test",
        targets = targets,
    )
    native.test_suite(
        name = name,
        tests = [name + "_clippy_test", name + "_format_test"],
    )
