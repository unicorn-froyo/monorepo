"""index.bzl provides the py_coverage_test rule"""

load("@bazel_skylib//lib:shell.bzl", "shell")
load("@rules_python//python:defs.bzl", "PyInfo")
load("//tools/coverage:config.bzl", "MINIMUM_LINE_COVERAGE")
load("//tools/testing/postgresql:providers.bzl", "PostgresqlFixtureInfo")

def _py_coverage_test(ctx):
    script = ctx.actions.declare_file(ctx.label.name + ".sh")
    manifest = ctx.actions.declare_file(ctx.label.name + ".sources.json")
    runtime_deps = ctx.attr.deps + ctx.attr.source_targets
    sources = depset(transitive = [dep[PyInfo].transitive_sources for dep in ctx.attr.source_targets])
    imports = depset(transitive = [dep[PyInfo].imports for dep in runtime_deps])
    ctx.actions.write(manifest, json.encode({
        "sources": [f.short_path for f in sources.to_list() if f.extension == "py"],
        "tests": [f.short_path for f in ctx.files.srcs],
        "imports": imports.to_list(),
    }))
    command = [ctx.executable._py_coverage_bin.short_path, "--manifest", manifest.short_path, "--config", ctx.file._coverage_config.short_path, "--minimum", str(MINIMUM_LINE_COVERAGE)]
    if ctx.attr.postgres:
        fixture = ctx.attr.postgres[PostgresqlFixtureInfo]
        command = [fixture.runner.short_path, "--fixture", fixture.manifest.short_path, "--"] + command
    ctx.actions.write(
        script,
        "#!/bin/sh\nset -eu\nexec %s\n" % " ".join([shell.quote(arg) for arg in command]),
        is_executable = True,
    )
    runfiles = ctx.runfiles(
        files = [manifest, ctx.file._coverage_config] + ctx.files.srcs + ctx.files.data,
        transitive_files = sources,
    )
    runfiles = runfiles.merge(ctx.attr._py_coverage_bin[DefaultInfo].default_runfiles)
    for dep in runtime_deps + ctx.attr.data:
        runfiles = runfiles.merge(dep[DefaultInfo].default_runfiles)
    if ctx.attr.postgres:
        runfiles = runfiles.merge(ctx.attr.postgres[DefaultInfo].default_runfiles)
    return [DefaultInfo(executable = script, runfiles = runfiles)]

_py_coverage_rule_test = rule(
    implementation = _py_coverage_test,
    attrs = {
        "postgres": attr.label(providers = [PostgresqlFixtureInfo]),
        "srcs": attr.label_list(
            allow_files = [".py"],
            providers = [PyInfo],
            mandatory = True,
            allow_empty = False,
        ),
        "source_targets": attr.label_list(
            providers = [PyInfo],
            mandatory = True,
            allow_empty = False,
            doc = "Application libraries/binaries whose workspace Python source closure is measured, including unimported files.",
        ),
        "deps": attr.label_list(
            providers = [PyInfo],
        ),
        "data": attr.label_list(
            allow_files = True,
        ),
        "_py_coverage_bin": attr.label(
            default = "//tools/coverage/python:coverage_bin",
            executable = True,
            cfg = "target",
        ),
        "_coverage_config": attr.label(
            default = "//tools/coverage/python:coverage_config",
            allow_single_file = True,
        ),
    },
    test = True,
)

def py_coverage_test(name, postgres = None, tags = None, **kwargs):
    """Run normal coverage, optionally with an isolated migrated PostgreSQL DB."""
    tags = list(tags or [])
    _py_coverage_rule_test(name = name, postgres = postgres, tags = tags, **kwargs)
