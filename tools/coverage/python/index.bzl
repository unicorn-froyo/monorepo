"""index.bzl provides the py_coverage_test rule"""

load("@rules_python//python:defs.bzl", "PyInfo")
load("//tools:utils.bzl", "get_transitive_deps")
load("//tools/coverage:config.bzl", "MINIMUM_LINE_COVERAGE")

def _py_coverage_test(ctx):
    script = ctx.actions.declare_file(ctx.label.name + ".sh")
    test_files = " ".join([s.short_path for s in ctx.files.srcs])

    imports = depset(transitive = [dep[PyInfo].imports for dep in ctx.attr.deps]).to_list()
    python_path = ":".join(["$RUNFILES_DIR/_main"] + ["$RUNFILES_DIR/" + path for path in imports])
    script_content = "\n".join([
        "#!/bin/sh",
        "export PYTHONPATH={python_path}".format(python_path = python_path),
        "set -e",
        "{coverage_bin} run --rcfile={config_path} -m unittest {files}".format(
            coverage_bin = ctx.executable._py_coverage_bin.short_path,
            files = test_files,
            config_path = ctx.files._coverage_config[0].short_path,
        ),
        "{coverage_bin} report --rcfile={config_path} --fail-under={minimum}".format(
            coverage_bin = ctx.executable._py_coverage_bin.short_path,
            config_path = ctx.files._coverage_config[0].short_path,
            minimum = MINIMUM_LINE_COVERAGE,
        ),
    ])

    ctx.actions.write(script, script_content, is_executable = True)

    runfiles = ctx.runfiles(
        files = [script] +
                ctx.files._coverage_py +
                ctx.files._coverage_config +
                ctx.files.srcs + ctx.files.deps +
                ctx.files.data + get_transitive_deps(ctx.attr.deps),
    )
    runfiles = runfiles.merge(ctx.attr._py_coverage_bin[DefaultInfo].default_runfiles)
    for dep in ctx.attr.deps:
        runfiles = runfiles.merge(dep[DefaultInfo].default_runfiles)

    return [DefaultInfo(
        executable = script,
        runfiles = runfiles,
    )]

py_coverage_test = rule(
    implementation = _py_coverage_test,
    attrs = {
        "srcs": attr.label_list(
            allow_files = True,
            providers = [PyInfo],
        ),
        "deps": attr.label_list(
            providers = [PyInfo],
        ),
        "data": attr.label_list(
            allow_files = True,
        ),
        "_py_coverage_bin": attr.label(
            default = "//tools/coverage/python:coverage_bin",
            executable = True,
            cfg = "exec",
        ),
        "_coverage_py": attr.label(
            default = "//third_party/pypi:coverage",
        ),
        "_coverage_config": attr.label(
            default = "//tools/coverage/python:coverage_config",
            allow_files = True,
        ),
    },
    test = True,
)
