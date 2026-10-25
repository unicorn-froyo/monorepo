"""Python lint, formatting, and type checks using pinned tools."""

load("@bazel_skylib//lib:shell.bzl", "shell")
load("@rules_python//python:defs.bzl", "PyInfo")

def _ruff_test(ctx, args):
    if not ctx.files.srcs:
        fail("Python lint and formatting checks require at least one source file")
    script = ctx.actions.declare_file(ctx.label.name + ".sh")
    ctx.actions.write(
        script,
        "#!/bin/sh\nset -eu\nexec %s\n" % " ".join([shell.quote(arg) for arg in [
            ctx.executable._ruff_bin.short_path,
        ] + args + ["--no-cache", "--config", ctx.file._config.short_path] + [f.short_path for f in ctx.files.srcs]]),
        is_executable = True,
    )
    runfiles = ctx.runfiles(files = ctx.files.srcs + ctx.files.data + [ctx.file._config])
    runfiles = runfiles.merge(ctx.attr._ruff_bin[DefaultInfo].default_runfiles)
    return [DefaultInfo(executable = script, runfiles = runfiles)]

def _py_lint_test(ctx):
    return _ruff_test(ctx, ["check"])

def _py_format_test(ctx):
    return _ruff_test(ctx, ["format", "--check"])

def _ruff_attrs():
    return {
        "srcs": attr.label_list(allow_files = [".py"]),
        # Retained for compatibility; Ruff does not import dependencies.
        "deps": attr.label_list(providers = [PyInfo]),
        "data": attr.label_list(allow_files = True),
        "_ruff_bin": attr.label(
            default = "//tools/lint/python:ruff_bin",
            executable = True,
            cfg = "exec",
        ),
        "_config": attr.label(
            default = "//tools/lint/python:ruff.toml",
            allow_single_file = True,
        ),
    }

py_lint_test = rule(
    implementation = _py_lint_test,
    attrs = _ruff_attrs(),
    test = True,
)

py_format_test = rule(
    implementation = _py_format_test,
    attrs = _ruff_attrs(),
    test = True,
)

def _py_typecheck_test(ctx):
    if not ctx.files.srcs:
        fail("py_typecheck_test requires at least one Python source file")
    imports = depset(transitive = [dep[PyInfo].imports for dep in ctx.attr.deps]).to_list()
    args = [
        ctx.executable._typecheck_bin.short_path,
        "--pyright",
        ctx.executable._pyright_bin.short_path,
        "--config",
        ctx.file._config.short_path,
        "--imports-json",
        json.encode(imports),
    ] + [f.short_path for f in ctx.files.srcs]
    script = ctx.actions.declare_file(ctx.label.name + ".sh")
    ctx.actions.write(
        script,
        "#!/bin/sh\nset -eu\nexec %s\n" % " ".join([shell.quote(arg) for arg in args]),
        is_executable = True,
    )
    runfiles = ctx.runfiles(files = ctx.files.srcs + ctx.files.data + [ctx.file._config])
    for dep in ctx.attr.deps + [ctx.attr._typecheck_bin, ctx.attr._pyright_bin]:
        runfiles = runfiles.merge(dep[DefaultInfo].default_runfiles)
    return [DefaultInfo(executable = script, runfiles = runfiles)]

py_typecheck_test = rule(
    implementation = _py_typecheck_test,
    attrs = {
        "srcs": attr.label_list(allow_files = [".py"], mandatory = True),
        "deps": attr.label_list(providers = [PyInfo]),
        "data": attr.label_list(allow_files = True),
        "_typecheck_bin": attr.label(
            default = "//tools/lint/python:typecheck_bin",
            executable = True,
            cfg = "exec",
        ),
        "_pyright_bin": attr.label(
            default = "//tools/lint/python:pyright_bin",
            executable = True,
            cfg = "exec",
        ),
        "_config": attr.label(
            default = "//tools/lint/python:pyrightconfig.json",
            allow_single_file = True,
        ),
    },
    test = True,
)
