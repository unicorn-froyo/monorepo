"""Java lint and formatting rules backed by pinned Maven tools."""

load("@bazel_skylib//lib:shell.bzl", "shell")

def _java_tool(ctx, args):
    if not ctx.files.srcs:
        fail("Java quality rules require at least one source file")
    script = ctx.actions.declare_file(ctx.label.name + ".sh")
    command = [ctx.executable._tool.short_path] + args + [f.short_path for f in ctx.files.srcs]
    ctx.actions.write(
        script,
        "#!/bin/sh\nset -eu\nexec %s\n" % " ".join([shell.quote(arg) for arg in command]),
        is_executable = True,
    )
    runfiles = ctx.runfiles(files = ctx.files.srcs + ctx.files._config)
    runfiles = runfiles.merge(ctx.attr._tool[DefaultInfo].default_runfiles)
    return [DefaultInfo(executable = script, runfiles = runfiles)]

def _java_lint_test(ctx):
    return _java_tool(ctx, ["-c", ctx.files._config[0].short_path])

def _java_format_test(ctx):
    return _java_tool(ctx, ["--dry-run", "--set-exit-if-changed"])

def _java_format_bin(ctx):
    return _java_tool(ctx, ["--replace"])

java_lint_test = rule(
    implementation = _java_lint_test,
    attrs = {
        "srcs": attr.label_list(allow_files = [".java"], mandatory = True),
        "_config": attr.label_list(default = ["//tools/lint/java:checkstyle.xml"], allow_files = True),
        "_tool": attr.label(default = "//tools/lint/java:checkstyle", executable = True, cfg = "exec"),
    },
    test = True,
)

java_format_test = rule(
    implementation = _java_format_test,
    attrs = {
        "srcs": attr.label_list(allow_files = [".java"], mandatory = True),
        "_config": attr.label_list(),
        "_tool": attr.label(default = "//tools/lint/java:google_java_format", executable = True, cfg = "exec"),
    },
    test = True,
)

java_format_bin = rule(
    implementation = _java_format_bin,
    attrs = {
        "srcs": attr.label_list(allow_files = [".java"], mandatory = True),
        "_config": attr.label_list(),
        "_tool": attr.label(default = "//tools/lint/java:google_java_format", executable = True, cfg = "exec"),
    },
    executable = True,
)
