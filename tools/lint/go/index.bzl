"""Go linting with the SDK's static analyzers (nogo)."""

load("@io_bazel_rules_go//go:def.bzl", "TOOLS_NOGO", "nogo")

def go_lint(name):
    """Create the analyzer used by go_sdk.nogo for workspace Go targets."""
    nogo(
        name = name,
        deps = TOOLS_NOGO,
        visibility = ["//visibility:public"],
    )
