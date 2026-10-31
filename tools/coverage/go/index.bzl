"""Go coverage tests using rules_go's native instrumentation."""

load("//tools/coverage/native:index.bzl", "coverage_attrs", "coverage_impl")
load("//tools/testing/postgresql:providers.bzl", "PostgresqlFixtureInfo")

def _go_coverage_test(ctx):
    if ctx.attr.postgres:
        fixture = ctx.attr.postgres[PostgresqlFixtureInfo]
        return coverage_impl(
            ctx,
            "go",
            command_prefix = [fixture.runner.short_path, "--fixture", fixture.manifest.short_path, "--"],
            extra_runfiles = ctx.attr.postgres[DefaultInfo].default_runfiles,
        )
    return coverage_impl(ctx, "go")

def _attrs():
    attrs = coverage_attrs()
    attrs["postgres"] = attr.label(providers = [PostgresqlFixtureInfo])
    return attrs

go_coverage_test = rule(
    implementation = _go_coverage_test,
    attrs = _attrs(),
    test = True,
)
