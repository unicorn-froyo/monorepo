"""Python lint tests backed by Ruff."""

load("@rules_python//python:defs.bzl", "PyInfo")

def _py_lint_test(ctx):
    script = ctx.actions.declare_file(ctx.label.name + ".sh")
    ctx.actions.write(
        script,
        "#!/bin/sh\nset -eu\nexec %s check --no-cache --config %s %s\n" % (
            ctx.executable._ruff_bin.short_path,
            ctx.file._config.short_path,
            " ".join(["'%s'" % f.short_path.replace("'", "'\\''") for f in ctx.files.srcs]),
        ),
        is_executable = True,
    )
    runfiles = ctx.runfiles(files = ctx.files.srcs + ctx.files.data + [ctx.file._config])
    runfiles = runfiles.merge(ctx.attr._ruff_bin[DefaultInfo].default_runfiles)
    return [DefaultInfo(executable = script, runfiles = runfiles)]

py_lint_test = rule(
    implementation = _py_lint_test,
    attrs = {
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
    },
    test = True,
)
