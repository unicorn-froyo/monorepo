"""Ruby test coverage with SimpleCov and LCOV reports."""

load("@rules_ruby//ruby:defs.bzl", "rb_test")

def rb_coverage_test(name, srcs, deps = []):
    """Run one Ruby test script with coverage started before application imports."""
    if len(srcs) != 1:
        fail("rb_coverage_test requires exactly one test script")
    rb_test(
        name = name,
        srcs = srcs + ["//tools/coverage/ruby:coverage_bin.rb"],
        main = "//tools/coverage/ruby:coverage_bin.rb",
        args = ["$(location %s)" % srcs[0]],
        deps = deps + ["@bundle"],
    )
