"""Language-independent Flyway migration bundles and static schema checks."""

load("@bazel_skylib//lib:shell.bzl", "shell")

FlywayMigrationsInfo = provider(fields = ["manifest", "sql_files", "script_configs", "schema", "history_table"])

def _migrations(ctx):
    names = {}
    for src in ctx.files.srcs:
        if src.basename in names:
            fail("Duplicate migration filename: " + src.basename)
        names[src.basename] = True
    manifest = ctx.actions.declare_file(ctx.label.name + ".json")
    ctx.actions.write(manifest, json.encode({
        "sql_files": [f.short_path for f in ctx.files.srcs],
        "script_configs": [f.short_path for f in ctx.files.script_configs],
        "schema": ctx.attr.schema,
        "history_table": ctx.attr.history_table,
    }))
    files = ctx.files.srcs + ctx.files.script_configs + [manifest]
    return [
        DefaultInfo(files = depset(files), runfiles = ctx.runfiles(files = files)),
        FlywayMigrationsInfo(manifest = manifest, sql_files = ctx.files.srcs, script_configs = ctx.files.script_configs, schema = ctx.attr.schema, history_table = ctx.attr.history_table),
    ]

flyway_migrations = rule(
    implementation = _migrations,
    attrs = {
        "srcs": attr.label_list(allow_files = [".sql"], mandatory = True, allow_empty = False),
        "script_configs": attr.label_list(allow_files = [".conf"]),
        "schema": attr.string(mandatory = True),
        "history_table": attr.string(default = "flyway_schema_history"),
    },
)

def _schema_test(ctx):
    manifest = ctx.attr.migrations[FlywayMigrationsInfo].manifest
    script = ctx.actions.declare_file(ctx.label.name + ".sh")
    ctx.actions.write(script, "#!/bin/sh\nset -eu\nexec %s --manifest %s --config %s\n" % (
        shell.quote(ctx.executable._checker.short_path),
        shell.quote(manifest.short_path),
        shell.quote(ctx.file.lint_config.short_path),
    ), is_executable = True)
    runfiles = ctx.runfiles(files = [ctx.file.lint_config])
    for target in [ctx.attr.migrations, ctx.attr._checker]:
        runfiles = runfiles.merge(target[DefaultInfo].default_runfiles)
    return [DefaultInfo(executable = script, runfiles = runfiles)]

flyway_schema_test = rule(
    implementation = _schema_test,
    attrs = {
        "migrations": attr.label(providers = [FlywayMigrationsInfo], mandatory = True),
        "lint_config": attr.label(default = "//tools/migrations/flyway:sqlfluff.cfg", allow_single_file = True),
        "_checker": attr.label(default = "//tools/migrations/python:schema_test", executable = True, cfg = "target"),
    },
    test = True,
)
