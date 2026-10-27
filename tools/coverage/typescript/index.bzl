"""Coverage for compiled TypeScript node:test suites."""

load("@bazel_skylib//lib:shell.bzl", "shell")
load("//tools/coverage:config.bzl", "MINIMUM_LINE_COVERAGE")

def _ts_coverage_test(ctx):
    if not ctx.files.srcs:
        fail("ts_coverage_test requires at least one intended TypeScript source")

    script = ctx.actions.declare_file(ctx.label.name + ".sh")
    command = [
        ctx.executable._coverage_runner.short_path,
        "--c8",
        ctx.executable._c8.short_path,
        "--entry-point",
        ctx.attr.entry_point,
        "--minimum",
        str(MINIMUM_LINE_COVERAGE),
    ]
    for src in ctx.files.srcs:
        command.extend(["--source", src.short_path])
    ctx.actions.write(
        script,
        "#!/bin/sh\nset -eu\nexport NODE_PATH=third_party/npm/node_modules\nexec %s\n" % " ".join([shell.quote(arg) for arg in command]),
        is_executable = True,
    )

    runfiles = ctx.runfiles(files = ctx.files.srcs + ctx.files.data)
    for dep in ctx.attr.data + [ctx.attr._c8, ctx.attr._coverage_runner]:
        runfiles = runfiles.merge(dep[DefaultInfo].default_runfiles)
    return [DefaultInfo(executable = script, runfiles = runfiles)]

ts_coverage_test = rule(
    implementation = _ts_coverage_test,
    attrs = {
        "srcs": attr.label_list(
            allow_files = [".ts"],
            mandatory = True,
            allow_empty = False,
            doc = "Intended workspace TypeScript application sources, including never-imported files.",
        ),
        "entry_point": attr.string(mandatory = True),
        "data": attr.label_list(allow_files = True),
        "_c8": attr.label(
            default = "//tools/coverage/typescript:c8_bin",
            executable = True,
            cfg = "target",
        ),
        "_coverage_runner": attr.label(
            default = "//tools/coverage/typescript:coverage_runner",
            executable = True,
            cfg = "target",
        ),
    },
    test = True,
)
