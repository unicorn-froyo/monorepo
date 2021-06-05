"""index.bzl provides the packaging ruleset"""

load("@rules_python//python:defs.bzl", "PyInfo")
load("//tools:utils.bzl", "get_transitive_deps")
load("//tools:providers.bzl", "PackageInfo")

def _package_api(ctx):
    language = None
    if PyInfo in ctx.attr.srcs[0]:
        language = "python"
    output_file = ctx.actions.declare_file(ctx.attr.name + ".zip")
    files = ctx.files._packaging_bin + ctx.files._python_bin + ctx.files.srcs + ctx.files.data + get_transitive_deps(ctx.attr.srcs)
    args = ctx.actions.args()
    args.add_joined([s.path for s in get_transitive_deps(ctx.attr.srcs)], join_with = ",")
    args.add("--output-file", output_file.path)
    args.add("--runtime", language)
    ctx.actions.run(
        mnemonic = "Packaging",
        executable = ctx.executable._packaging_bin,
        arguments = [args],
        inputs = files,
        outputs = [output_file],
    )

    return [
        DefaultInfo(
            files = depset([output_file]),
        ),
        PackageInfo(language = language),
    ]

package_api = rule(
    implementation = _package_api,
    attrs = {
        "srcs": attr.label_list(
            providers = [PyInfo],
        ),
        "data": attr.label_list(
            allow_files = True,
        ),
        "_packaging_bin": attr.label(
            default = "//tools/package:package_api_bin",
            executable = True,
            cfg = "exec",
        ),
        "_python_bin": attr.label(
            default = "@python_interpreter//:python_bin",
            executable = True,
            cfg = "exec",
            allow_files = True,
        ),
    },
)
