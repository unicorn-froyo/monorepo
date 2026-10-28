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
    if not srcs:
        fail("ts_format_test requires at least one TypeScript source")
    script = "\n".join([
        "#!/bin/sh",
        "set -eu",
        "format_tmp=\"${TEST_TMPDIR}/typescript-format\"",
        "mkdir -p \"${format_tmp}\"",
    ] + [
        "cp %%SOURCE_%d%% \"${format_tmp}/%s\"" % (index, src.split(":")[-1])
        for index, src in enumerate(srcs)
    ] + [
        "exec %s --check %s" % (
            "%PRETTIER%",
            " ".join(["\"${format_tmp}/%s\"" % src.split(":")[-1] for src in srcs]),
        ),
    ])
    _format_rule_test(
        name = name,
        srcs = srcs,
        script = script,
        mode = "check",
    )

def ts_format_bin(name, srcs):
    """Create a runnable target that formats TypeScript sources in place."""
    if not srcs:
        fail("ts_format_bin requires at least one TypeScript source")
    command = [
        "#!/bin/sh",
        "set -eu",
        "workspace=\"${BUILD_WORKSPACE_DIRECTORY:?run this target with bazel run}\"",
        "exec %s --write %s" % (
            "%PRETTIER%",
            " ".join(["\"${workspace}/%%SOURCE_%d%%\"" % index for index, _ in enumerate(srcs)]),
        ),
    ]
    _format_binary_rule(
        name = name,
        srcs = srcs,
        script = "\n".join(command),
        mode = "write",
    )

def _format_impl(ctx):
    if not ctx.files.srcs:
        fail("TypeScript formatting requires at least one source file")
    script = ctx.actions.declare_file(ctx.label.name + ".sh")
    script_content = ctx.attr.script
    source_targets = ctx.attr.srcs
    prettier_target = ctx.attr._prettier
    targets = source_targets + [prettier_target]
    for index, target in enumerate(source_targets):
        if ctx.attr.mode == "check":
            expanded = ctx.expand_location("$(rootpath %s)" % target.label, targets = targets)
            script_content = script_content.replace("%%SOURCE_%d%%" % index, shell.quote(expanded))
        else:
            workspace_path = target.label.package + "/" + target.label.name.split(":")[-1]
            script_content = script_content.replace("%%SOURCE_%d%%" % index, workspace_path)
    prettier_path = shell.quote(ctx.expand_location("$(rootpath %s)" % prettier_target.label, targets = targets))
    ctx.actions.write(
        script,
        script_content.replace("%PRETTIER%", prettier_path),
        is_executable = True,
    )
    runfiles = ctx.runfiles(files = ctx.files.srcs)
    runfiles = runfiles.merge(ctx.attr._prettier[DefaultInfo].default_runfiles)
    return [DefaultInfo(executable = script, runfiles = runfiles)]

_format_attrs = {
    "srcs": attr.label_list(allow_files = [".ts"], mandatory = True, allow_empty = False),
    "script": attr.string(mandatory = True),
    "mode": attr.string(values = ["check", "write"], mandatory = True),
    "_prettier": attr.label(
        default = "//tools/lint/typescript:prettier_bin",
        executable = True,
        cfg = "target",
    ),
}

_format_rule_test = rule(implementation = _format_impl, attrs = _format_attrs, test = True)
_format_binary_rule = rule(implementation = _format_impl, attrs = _format_attrs, executable = True)
