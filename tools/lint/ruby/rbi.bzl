"""Build dependency interfaces and update schema-backed Ruby model interfaces."""

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

def _rb_gem_rbis(ctx):
    output = ctx.actions.declare_directory(ctx.label.name + "_generated")
    ctx.actions.run_shell(
        inputs = ctx.files.srcs,
        tools = [ctx.attr.generator[DefaultInfo].files_to_run],
        outputs = [output],
        arguments = [ctx.executable.generator.path, output.path, ctx.workspace_name],
        command = """set -eu
execroot="$PWD"
cd "$1.runfiles/$3"
exec "$execroot/$1" "$execroot/$2"
""",
        mnemonic = "RubyGemRbis",
        progress_message = "Generating Ruby dependency interfaces",
    )
    return [DefaultInfo(files = depset([output]), runfiles = ctx.runfiles(files = [output]))]

rb_gem_rbis = rule(
    implementation = _rb_gem_rbis,
    attrs = {
        "srcs": attr.label_list(allow_files = True),
        "generator": attr.label(
            default = "//tools/lint/ruby:gem_rbi_generator",
            executable = True,
            cfg = "exec",
        ),
    },
    doc = "Generate dependency RBIs as a cached build output from the locked Ruby bundle.",
)
