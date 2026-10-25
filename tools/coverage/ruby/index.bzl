"""Ruby test coverage with SimpleCov and LCOV reports."""

load("@rules_ruby//ruby:defs.bzl", "rb_test")
load("//tools/coverage:config.bzl", "MINIMUM_LINE_COVERAGE")

def rb_coverage_test(name, srcs, deps = [], data = []):
    """Run Ruby test scripts in order with coverage started before imports."""
    if not srcs:
        fail("rb_coverage_test requires at least one test script")
    rb_test(
        name = name,
        srcs = srcs + ["//tools/coverage/ruby:coverage_bin.rb"],
        main = "//tools/coverage/ruby:coverage_bin.rb",
        args = ["$(location %s)" % src for src in srcs],
        deps = deps + ["@bundle"],
        data = data,
        env = {"MINIMUM_LINE_COVERAGE": str(MINIMUM_LINE_COVERAGE)},
    )
