"""Ruby test coverage with SimpleCov and LCOV reports."""

load("@rules_ruby//ruby:defs.bzl", "rb_test")
load("//tools/coverage:config.bzl", "MINIMUM_LINE_COVERAGE")

def rb_coverage_test(name, srcs, deps = [], data = []):
    """Run Ruby test scripts and preserve a validated portable LCOV report."""
    if not srcs:
        fail("rb_coverage_test requires at least one test script")
    rb_test(
        name = name,
        srcs = srcs + [
            "//tools/coverage/ruby:coverage_bin.rb",
            "//tools/coverage/ruby:lcov.rb",
        ],
        main = "//tools/coverage/ruby:coverage_bin.rb",
        args = ["$(location %s)" % src for src in srcs],
        data = data,
        deps = deps + ["@bundle"],
        env = {"MINIMUM_LINE_COVERAGE": str(MINIMUM_LINE_COVERAGE)},
    )
