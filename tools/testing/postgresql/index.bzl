"""Declare PostgreSQL fixtures without starting resources at analysis time."""

load("@bazel_skylib//lib:shell.bzl", "shell")
load("//tools/migrations/flyway:index.bzl", "FlywayMigrationsInfo")
load(":providers.bzl", "PostgresqlFixtureInfo")

def _fixture(ctx):
    if min(ctx.attr.startup_timeout_seconds, ctx.attr.migration_timeout_seconds) <= 0:
        fail("PostgreSQL fixture timeouts must be positive")
    bundle = ctx.attr.migrations[FlywayMigrationsInfo]
    manifest = ctx.actions.declare_file(ctx.label.name + ".fixture.json")
    ctx.actions.write(manifest, json.encode({
        "migrations": bundle.manifest.short_path,
        "initdb": ctx.file._initdb.short_path,
        "postgres": ctx.file._postgres.short_path,
        "flyway": ctx.executable._flyway.short_path,
        "database": ctx.attr.database,
        "startup_timeout_seconds": ctx.attr.startup_timeout_seconds,
        "migration_timeout_seconds": ctx.attr.migration_timeout_seconds,
    }))
    runfiles = ctx.runfiles(files = [manifest] + ctx.files._distribution)
    for target in [ctx.attr.migrations, ctx.attr._runner, ctx.attr._flyway]:
        runfiles = runfiles.merge(target[DefaultInfo].default_runfiles)
    return [
        DefaultInfo(files = depset([manifest]), runfiles = runfiles),
        PostgresqlFixtureInfo(manifest = manifest, runner = ctx.executable._runner),
    ]

postgresql_fixture = rule(
    implementation = _fixture,
    attrs = {
        "migrations": attr.label(providers = [FlywayMigrationsInfo], mandatory = True),
        "database": attr.string(default = "testdb"),
        "startup_timeout_seconds": attr.int(default = 30),
        "migration_timeout_seconds": attr.int(default = 60),
        "_initdb": attr.label(default = "//third_party/postgresql:initdb", allow_single_file = True),
        "_postgres": attr.label(default = "//third_party/postgresql:postgres", allow_single_file = True),
        "_distribution": attr.label(default = "//third_party/postgresql:distribution"),
        "_runner": attr.label(default = "//tools/testing/python:postgresql_runner", executable = True, cfg = "target"),
        "_flyway": attr.label(default = "//tools/migrations/flyway:cli", executable = True, cfg = "target"),
    },
)

def _dev(ctx):
    fixture = ctx.attr.fixture[PostgresqlFixtureInfo]
    script = ctx.actions.declare_file(ctx.label.name + ".sh")
    ctx.actions.write(script, "#!/bin/sh\nset -eu\nexec %s --fixture %s --dev --image %s\n" % (
        shell.quote(fixture.runner.short_path),
        shell.quote(fixture.manifest.short_path),
        shell.quote(ctx.file.image.short_path),
    ), is_executable = True)
    return [DefaultInfo(executable = script, runfiles = ctx.attr.fixture[DefaultInfo].default_runfiles.merge(ctx.runfiles(files = [ctx.file.image])))]

postgresql_dev = rule(
    implementation = _dev,
    attrs = {
        "fixture": attr.label(providers = [PostgresqlFixtureInfo], mandatory = True),
        "image": attr.label(default = "//tools/testing/postgresql:postgres_image", allow_single_file = [".tar"]),
    },
    executable = True,
)
