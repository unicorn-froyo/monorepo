"""Ruby lint and formatting checks using the locked RuboCop bundle."""

load("@bazel_skylib//lib:shell.bzl", "shell")
load("@rules_ruby//ruby:defs.bzl", "rb_test")

def rb_lint_test(name, srcs):
    """Check Ruby sources, including test files and Rack configuration."""
    rb_test(
        name = name,
        main = "@bundle//bin:rubocop",
        args = ["--config", "$(location //tools/lint/ruby:config)"] + ["$(location %s)" % src for src in srcs],
        data = srcs + ["//tools/lint/ruby:config"],
        deps = ["@bundle"],
    )

def rb_format_test(name, srcs):
    """Check Ruby formatting with RuboCop's layout cops."""
    rb_test(
        name = name,
        main = "@bundle//bin:rubocop",
        args = [
            "--config",
            "$(location //tools/lint/ruby:config)",
            "--only",
            "Layout",
        ] + ["$(location %s)" % src for src in srcs],
        data = srcs + ["//tools/lint/ruby:config"],
        deps = ["@bundle"],
    )

def _rb_format_bin(ctx):
    if not ctx.files.srcs:
        fail("rb_format_bin requires at least one Ruby source file")
    script = ctx.actions.declare_file(ctx.label.name + ".sh")
    command = [
        ctx.executable._rubocop.short_path,
        "--config",
        ctx.file._config.short_path,
        "--autocorrect-all",
    ] + [src.short_path for src in ctx.files.srcs]
    ctx.actions.write(
        script,
        "#!/bin/sh\nset -eu\nexec %s\n" % " ".join([shell.quote(arg) for arg in command]),
        is_executable = True,
    )
    runfiles = ctx.runfiles(files = ctx.files.srcs + [ctx.file._config])
    runfiles = runfiles.merge(ctx.attr._rubocop[DefaultInfo].default_runfiles)
    return [DefaultInfo(executable = script, runfiles = runfiles)]

rb_format_bin = rule(
    implementation = _rb_format_bin,
    attrs = {
        "srcs": attr.label_list(allow_files = [".rb", ".ru"], mandatory = True),
        "_config": attr.label(
            default = "//tools/lint/ruby:config",
            allow_single_file = True,
        ),
        "_rubocop": attr.label(
            default = "@bundle//bin:rubocop",
            executable = True,
            cfg = "exec",
        ),
    },
    executable = True,
)
