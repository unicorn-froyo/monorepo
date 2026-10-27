"""Rust lint and formatting rules backed by Clippy and rustfmt."""

load("@bazel_skylib//lib:shell.bzl", "shell")
load("@rules_rust//rust:defs.bzl", "rust_clippy_test", "rustfmt_test")

def rs_lint_test(name, targets):
    """Check Rust targets for Clippy findings."""
    rust_clippy_test(
        name = name,
        targets = targets,
    )

def rs_format_test(name, targets):
    """Check Rust target formatting with rustfmt."""
    rustfmt_test(
        name = name,
        targets = targets,
    )

def _rs_format_bin(ctx):
    if not ctx.files.srcs:
        fail("rs_format_bin requires at least one Rust source file")
    rustfmt_toolchain = ctx.toolchains["@rules_rust//rust/rustfmt:toolchain_type"]
    script = ctx.actions.declare_file(ctx.label.name + ".sh")
    command = [
        rustfmt_toolchain.rustfmt.short_path,
        "--edition",
        ctx.attr.edition,
    ] + [src.short_path for src in ctx.files.srcs]
    ctx.actions.write(
        script,
        "#!/bin/sh\nset -eu\nexec %s\n" % " ".join([shell.quote(arg) for arg in command]),
        is_executable = True,
    )
    runfiles = ctx.runfiles(
        files = ctx.files.srcs,
        transitive_files = rustfmt_toolchain.all_files,
    )
    return [DefaultInfo(executable = script, runfiles = runfiles)]

rs_format_bin = rule(
    implementation = _rs_format_bin,
    attrs = {
        "edition": attr.string(default = "2021"),
        "srcs": attr.label_list(allow_files = [".rs"], mandatory = True),
    },
    executable = True,
    toolchains = ["@rules_rust//rust/rustfmt:toolchain_type"],
)
