"""index.bzl provides the py_coverage_test rule"""

load("//tools:providers.bzl", "PackageInfo")

def _deploy_api_impl(ctx):
    script = ctx.actions.declare_file(ctx.label.name + ".sh")
    script_content = "\n".join([
        "#!/bin/sh",
    ])

    ctx.actions.write(script, script_content, is_executable = True)

    return [DefaultInfo(
        executable = script,
        runfiles = ctx.runfiles(
            files = [script] +
                    ctx.files.package,
        ),
    )]

deploy_api = rule(
    implementation = _deploy_api_impl,
    attrs = {
        "package": attr.label(
            providers = [PackageInfo],
        ),
    },
)
