"""Ruby test coverage with SimpleCov and LCOV reports."""

load("@rules_ruby//ruby:defs.bzl", "rb_binary", "rb_test")
load("//tools/coverage:config.bzl", "MINIMUM_LINE_COVERAGE")
load(":postgresql.bzl", "rb_postgresql_test")

def rb_coverage_test(name, srcs, deps = [], data = [], postgres = None, sources = []):
    """Run Ruby test scripts and preserve a validated portable LCOV report."""
    if not sources:
        fail("rb_coverage_test requires intended application sources")
    if not srcs:
        fail("rb_coverage_test requires at least one test script")
    srcs = [str(native.package_relative_label(src)) for src in srcs]
    sources = [str(native.package_relative_label(source)) for source in sources]
    runner = rb_binary if postgres else rb_test
    runner(
        name = name + "_runner" if postgres else name,
        srcs = depset(srcs + sources + [
            str(Label("//tools/coverage/ruby:coverage_bin.rb")),
            str(Label("//tools/coverage/ruby:lcov.rb")),
        ]).to_list(),
        main = str(Label("//tools/coverage/ruby:coverage_bin.rb")),
        args = ["$(location %s)" % src for src in srcs],
        data = data,
        deps = deps + ["@bundle"],
        env = {
            "MINIMUM_LINE_COVERAGE": str(MINIMUM_LINE_COVERAGE),
            "RUBY_COVERAGE_SOURCES": ":".join(["$(location %s)" % source for source in sources]),
        },
    )

    if postgres:
        rb_postgresql_test(
            name = name,
            test = ":" + name + "_runner",
            srcs = srcs,
            postgres = postgres,
            size = "large",
            timeout = "long",
        )
