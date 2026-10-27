"""TypeScript linting and formatting with pinned ESLint and Prettier."""

load("@bazel_skylib//lib:shell.bzl", "shell")
load("@npm//third_party/npm:eslint/package_json.bzl", "bin")

def ts_lint_test(name, srcs):
    """Lint the given TypeScript source and test files."""
    bin.eslint_test(
        name = name,
        data = srcs + [
            "//tools/lint/typescript:config",
            "//third_party/npm:node_modules/@eslint/js",
            "//third_party/npm:node_modules/typescript-eslint",
        ],
        args = ["--config", "$(rootpath //tools/lint/typescript:config)", "--max-warnings=0"] + ["$(rootpath %s)" % src for src in srcs],
    )

def ts_format_test(name, srcs):
    """Check TypeScript formatting with the pinned Prettier release."""
    _ts_format_rule_test(
        name = name,
        mode = "check",
        srcs = srcs,
    )

def ts_format_bin(name, srcs):
    """Create a runnable target that formats TypeScript sources in place."""
    _ts_format_binary(
        name = name,
        mode = "write",
        srcs = srcs,
    )

def _ts_format(ctx):
    if not ctx.files.srcs:
        fail("TypeScript formatting requires at least one source file")
    script = ctx.actions.declare_file(ctx.label.name + ".sh")
    command = [
        ctx.executable._runner.short_path,
        "--prettier",
        ctx.executable._prettier.short_path,
        "--mode",
        ctx.attr.mode,
    ]
    for src in ctx.files.srcs:
        command.extend(["--source", src.short_path])
    ctx.actions.write(
        script,
        "#!/bin/sh\nset -eu\nexec %s\n" % " ".join([shell.quote(arg) for arg in command]),
        is_executable = True,
    )
    runfiles = ctx.runfiles(files = ctx.files.srcs)
    for dep in [ctx.attr._prettier, ctx.attr._runner]:
        runfiles = runfiles.merge(dep[DefaultInfo].default_runfiles)
    return [DefaultInfo(executable = script, runfiles = runfiles)]

_format_attrs = {
    "srcs": attr.label_list(allow_files = [".ts"], mandatory = True, allow_empty = False),
    "mode": attr.string(values = ["check", "write"], mandatory = True),
    "_prettier": attr.label(
        default = "//tools/lint/typescript:prettier_bin",
        executable = True,
        cfg = "target",
    ),
    "_runner": attr.label(
        default = "//tools/lint/typescript:format_runner",
        executable = True,
        cfg = "target",
    ),
}

_ts_format_rule_test = rule(implementation = _ts_format, attrs = _format_attrs, test = True)
_ts_format_binary = rule(implementation = _ts_format, attrs = _format_attrs, executable = True)
