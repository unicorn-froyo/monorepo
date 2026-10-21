"""Go coverage tests using rules_go's native instrumentation."""

load("//tools/coverage/native:index.bzl", "coverage_attrs", "coverage_impl")

def _go_coverage_test(ctx):
    return coverage_impl(ctx, "go")

go_coverage_test = rule(
    implementation = _go_coverage_test,
    attrs = coverage_attrs(),
    test = True,
)
