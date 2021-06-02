"""index.bzl provides the packaging ruleset"""

load("@rules_python//python:defs.bzl", "PyInfo")
load("//tools:utils.bzl", "get_transitive_deps")

def _package_api(ctx):
    # script = ctx.actions.declare_file(ctx.label.name + ".sh")
    output_file = ctx.actions.declare_file("package.zip")

    args = ctx.actions.args()
    args.add_joined([s.short_path for s in get_transitive_deps(ctx.attr.srcs)], join_with = ",")
    ctx.actions.run(
        mnemonic = "Packaging",
        executable = ctx.executable._packaging_bin,
        arguments = [args],
        # inputs = inputs,
        outputs = [output_file],
    )

    # ctx.actions.write(
    #     output = output_file,
    #     content = "hello",
    # )
    print(output_file.short_path)

    # ctx.actions.write(script, script_content, is_executable = True)
    return [DefaultInfo(
        # executable = script,
        runfiles = ctx.runfiles(
            files =
                # [script] +
                ctx.files._packaging_bin +
                ctx.files._python_bin +
                ctx.files.srcs +
                ctx.files.data +
                get_transitive_deps(ctx.attr.srcs),
        ),
    )]

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
    outputs = {"zip": "package.zip"},
)
