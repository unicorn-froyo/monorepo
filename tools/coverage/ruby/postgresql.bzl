"""Run Ruby coverage executables inside the shared PostgreSQL fixture."""

load("@bazel_skylib//lib:shell.bzl", "shell")
load("//tools/testing/postgresql:providers.bzl", "PostgresqlFixtureInfo")

def _rb_postgresql_test(ctx):
    fixture = ctx.attr.postgres[PostgresqlFixtureInfo]
    script = ctx.actions.declare_file(ctx.label.name + ".sh")
    command = [fixture.runner.short_path, "--fixture", fixture.manifest.short_path, "--", ctx.executable.test.short_path] + [src.short_path for src in ctx.files.srcs]
    ctx.actions.write(script, "#!/bin/sh\nset -eu\nexec %s\n" % " ".join([shell.quote(arg) for arg in command]), is_executable = True)
    runfiles = ctx.runfiles(files = ctx.files.srcs).merge(ctx.attr.postgres[DefaultInfo].default_runfiles).merge(ctx.attr.test[DefaultInfo].default_runfiles)
    return [DefaultInfo(executable = script, runfiles = runfiles)]

rb_postgresql_test = rule(
    implementation = _rb_postgresql_test,
    attrs = {
        "srcs": attr.label_list(allow_files = [".rb"]),
        "postgres": attr.label(providers = [PostgresqlFixtureInfo], mandatory = True),
        "test": attr.label(executable = True, cfg = "target", mandatory = True),
    },
    test = True,
)
