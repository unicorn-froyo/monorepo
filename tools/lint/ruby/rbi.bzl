"""Generate checked-in Ruby interfaces using the migrated PostgreSQL fixture."""

load("@bazel_skylib//lib:shell.bzl", "shell")
load("//tools/testing/postgresql:providers.bzl", "PostgresqlFixtureInfo")

def _rb_rbi_update(ctx):
    fixture = ctx.attr.postgres[PostgresqlFixtureInfo]
    script = ctx.actions.declare_file(ctx.label.name + ".sh")
    command = [fixture.runner.short_path, "--fixture", fixture.manifest.short_path, "--", ctx.executable.generator.short_path, "--update"]

    # Keep the shell alive to remove its private scratch directory after the fixture exits.
    ctx.actions.write(script, """#!/bin/sh
set -eu
: "${BUILD_WORKSPACE_DIRECTORY:?Run this target with bazel run}"
tmp=$(mktemp -d)
trap 'rm -rf "$tmp"' EXIT
export TEST_TMPDIR="$tmp"
export TEST_UNDECLARED_OUTPUTS_DIR="$tmp/outputs"
mkdir -p "$TEST_UNDECLARED_OUTPUTS_DIR"
%s
""" % " ".join([shell.quote(arg) for arg in command]), is_executable = True)
    runfiles = ctx.attr.postgres[DefaultInfo].default_runfiles.merge(ctx.attr.generator[DefaultInfo].default_runfiles)
    return [DefaultInfo(executable = script, runfiles = runfiles)]

rb_rbi_update = rule(
    implementation = _rb_rbi_update,
    attrs = {
        "postgres": attr.label(providers = [PostgresqlFixtureInfo], mandatory = True),
        "generator": attr.label(executable = True, cfg = "target", mandatory = True),
    },
    executable = True,
)
