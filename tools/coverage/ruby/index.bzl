"""Ruby test coverage with SimpleCov and LCOV reports."""

load("@bazel_skylib//lib:shell.bzl", "shell")
load("@rules_ruby//ruby:defs.bzl", "rb_binary", "rb_test")
load("//tools/coverage:config.bzl", "MINIMUM_LINE_COVERAGE")
load("//tools/testing/postgresql:providers.bzl", "PostgresqlFixtureInfo")

def rb_coverage_test(name, srcs, deps = [], data = [], postgres = None, sources = [], visibility = None):
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
        visibility = ["//visibility:private"] if postgres else visibility,
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
        _rb_postgresql_coverage_test(
            name = name,
            visibility = visibility,
            test = ":" + name + "_runner",
            srcs = srcs,
            postgres = postgres,
            size = "large",
            timeout = "long",
        )

def _rb_postgresql_test(ctx):
    fixture = ctx.attr.postgres[PostgresqlFixtureInfo]
    script = ctx.actions.declare_file(ctx.label.name + ".sh")
    command = [fixture.runner.short_path, "--fixture", fixture.manifest.short_path, "--", ctx.executable.test.short_path] + [src.short_path for src in ctx.files.srcs]
    ctx.actions.write(script, "#!/bin/sh\nset -eu\nexec %s\n" % " ".join([shell.quote(arg) for arg in command]), is_executable = True)
    runfiles = ctx.runfiles(files = ctx.files.srcs).merge(ctx.attr.postgres[DefaultInfo].default_runfiles).merge(ctx.attr.test[DefaultInfo].default_runfiles)
    return [DefaultInfo(executable = script, runfiles = runfiles)]

_rb_postgresql_coverage_test = rule(
    implementation = _rb_postgresql_test,
    attrs = {
        "srcs": attr.label_list(allow_files = [".rb"]),
        "postgres": attr.label(providers = [PostgresqlFixtureInfo], mandatory = True),
        "test": attr.label(executable = True, cfg = "target", mandatory = True),
    },
    test = True,
)
