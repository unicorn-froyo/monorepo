"""Go linting and formatting with the hermetic Go SDK."""

load("@bazel_skylib//lib:shell.bzl", "shell")
load("@io_bazel_rules_go//go:def.bzl", "GoInfo", "TOOLS_NOGO", "nogo")

_GO_TOOLCHAIN = "@io_bazel_rules_go//go:toolchain"

def go_lint_analyzer(name):
    """Create the analyzer used by go_sdk.nogo for workspace Go targets."""
    nogo(
        name = name,
        deps = TOOLS_NOGO,
        visibility = ["//visibility:public"],
    )

def _go_lint_test(ctx):
    if not ctx.attr.targets:
        fail("go_lint_test requires at least one Go target")
    script = ctx.actions.declare_file(ctx.label.name + ".sh")
    ctx.actions.write(script, "#!/bin/sh\nexit 0\n", is_executable = True)
    runfiles = ctx.runfiles(
        transitive_files = depset(transitive = [target[DefaultInfo].files for target in ctx.attr.targets]),
    )
    return [DefaultInfo(executable = script, runfiles = runfiles)]

go_lint_test = rule(
    implementation = _go_lint_test,
    attrs = {
        "targets": attr.label_list(providers = [GoInfo], mandatory = True),
    },
    test = True,
)

def _gofmt(ctx, write):
    if not ctx.files.srcs:
        fail("Go formatting requires at least one source file")
    sdk = ctx.toolchains[_GO_TOOLCHAIN].sdk
    gofmt_files = [tool for tool in sdk.tools.to_list() if tool.basename == "gofmt"]
    if len(gofmt_files) != 1:
        fail("Go SDK must provide exactly one gofmt executable")
    gofmt = gofmt_files[0]
    script = ctx.actions.declare_file(ctx.label.name + ".sh")
    if write:
        sources = ['"$BUILD_WORKSPACE_DIRECTORY/%s"' % src.short_path for src in ctx.files.srcs]
        command = ': "${BUILD_WORKSPACE_DIRECTORY:?Run with bazel run}"\nexec %s -w %s\n' % (
            shell.quote(gofmt.short_path),
            " ".join(sources),
        )
    else:
        command = "output=$(%s -d %s)\n" % (
            shell.quote(gofmt.short_path),
            " ".join([shell.quote(src.short_path) for src in ctx.files.srcs]),
        )
        command += 'if [ -n "$output" ]; then printf "%s\\n" "$output"; exit 1; fi\n'
    ctx.actions.write(script, "#!/bin/sh\nset -eu\n" + command, is_executable = True)
    runfiles = ctx.runfiles(files = ctx.files.srcs, transitive_files = sdk.tools)
    return [DefaultInfo(executable = script, runfiles = runfiles)]

def _go_format_test(ctx):
    return _gofmt(ctx, False)

def _go_format_bin(ctx):
    return _gofmt(ctx, True)

_format_attrs = {
    "srcs": attr.label_list(allow_files = [".go"], mandatory = True),
}

go_format_test = rule(
    implementation = _go_format_test,
    attrs = _format_attrs,
    test = True,
    toolchains = [_GO_TOOLCHAIN],
)

go_format_bin = rule(
    implementation = _go_format_bin,
    attrs = _format_attrs,
    executable = True,
    toolchains = [_GO_TOOLCHAIN],
)

def _go_format_failure_test(ctx):
    script = ctx.actions.declare_file(ctx.label.name + ".sh")
    ctx.actions.write(
        script,
        "#!/bin/sh\nset -eu\nif '%s'; then\n" % ctx.executable.formatter.short_path +
        "  echo 'expected formatting check to fail' >&2\n  exit 1\nfi\n",
        is_executable = True,
    )
    runfiles = ctx.runfiles(files = [ctx.executable.formatter])
    runfiles = runfiles.merge(ctx.attr.formatter[DefaultInfo].default_runfiles)
    return [DefaultInfo(executable = script, runfiles = runfiles)]

go_format_failure_test = rule(
    implementation = _go_format_failure_test,
    attrs = {
        "formatter": attr.label(executable = True, cfg = "target", mandatory = True),
    },
    test = True,
)
