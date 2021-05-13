"""index.bzl provides the py_coverage_test rule"""

load("@rules_python//python:defs.bzl", "PyInfo")

def _py_coverage_test(ctx):
    script = ctx.actions.declare_file(ctx.label.name + ".sh")
    test_files = " ".join([s.short_path for s in ctx.files.srcs])

    python_path = ":".join([p.short_path for p in ctx.files._py_coverage_bin] + [s.short_path for s in ctx.files.srcs] + [s.short_path for s in ctx.files.deps])
    script_content = "\n".join([
        "#!/bin/sh",
        "PYTHONPATH={python_path}".format(python_path = python_path),
        "{coverage_bin} run --rcfile={config_path} -m unittest {files}".format(
            coverage_bin = ctx.executable._py_coverage_bin.short_path,
            files = test_files,
            config_path = ctx.files._coverage_config[0].short_path,
        ),
        "{coverage_bin} report --rcfile={config_path}".format(
            coverage_bin = ctx.executable._py_coverage_bin.short_path,
            config_path = ctx.files._coverage_config[0].short_path,
        ),
    ])

    ctx.actions.write(script, script_content, is_executable = True)

    return [DefaultInfo(
        executable = script,
        runfiles = ctx.runfiles(
            files = [script] + ctx.files._py_coverage_bin + ctx.files._python_bin + ctx.files._coverage_py + ctx.files._coverage_config + ctx.files.srcs + ctx.files.deps + ctx.files.data,
        ),
    )]

py_coverage_test = rule(
    implementation = _py_coverage_test,
    attrs = {
        "srcs": attr.label_list(
            allow_files = True,
            providers = [PyInfo],
        ),
        "deps": attr.label_list(
            allow_files = True,
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
        "_python_bin": attr.label(
            default = "@python_interpreter//:python_bin",
            executable = True,
            cfg = "exec",
            allow_files = True,
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
