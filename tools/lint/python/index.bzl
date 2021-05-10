"""index.bzl provides the py_lint_test rule"""

load("@rules_python//python:defs.bzl", "PyInfo")

def get_transitive_files(label):
    """Get transitive sources for python files

    Args:
      label: A label of a python library.
    Returns:
      A list of transitive source files.
    """
    return label[PyInfo].transitive_sources.to_list()

def _py_lint_test(ctx):
    script = ctx.actions.declare_file(ctx.label.name + ".sh")
    test_files = " ".join([s.short_path for s in ctx.files.srcs])
    python_path = ":".join(
        [s.short_path for s in ctx.files.srcs] +
        [s.short_path for s in ctx.files.deps],
    )
    script_content = "\n".join([
        "#!/bin/sh",
        "PYTHONPATH={python_path}".format(python_path = python_path),
        "{linter_bin} {files} --rcfile={pylint_config}".format(
            linter_bin = ctx.executable._pylint_bin.short_path,
            files = test_files,
            pylint_config = ctx.files._pylint_config[0].short_path,
        ),
    ])

    ctx.actions.write(script, script_content, is_executable = True)

    return [
        DefaultInfo(
            executable = script,
            runfiles = ctx.runfiles(
                files = [script] + ctx.files._pylint_bin +
                        ctx.files._python_bin + ctx.files._pylint_config +
                        ctx.files.srcs + ctx.files.deps + ctx.files.data +
                        get_transitive_files(ctx.attr._pylint_py),
            ),
        ),
    ]

py_lint_test = rule(
    implementation = _py_lint_test,
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
        "_pylint_bin": attr.label(
            default = "//tools/lint/python:pylint_bin",
            executable = True,
            cfg = "exec",
        ),
        "_python_bin": attr.label(
            default = "@python_interpreter//:python_bin",
            executable = True,
            cfg = "exec",
            allow_files = True,
        ),
        "_pylint_py": attr.label(
            default = "//third_party/pypi:pylint",
            providers = [PyInfo],
        ),
        "_pylint_config": attr.label(
            default = "//tools/lint/python:pylint_config",
            allow_files = True,
        ),
    },
    test = True,
)
