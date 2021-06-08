"""index.bzl provides the py_coverage_test rule"""

load("//tools:providers.bzl", "DeploymentZoneInfo", "PackageInfo")

def _deploy_api_impl(ctx):
    package_path = ctx.files.package[0].short_path
    language = ctx.attr.package[PackageInfo].language
    account = ctx.attr.deployment_zone[DeploymentZoneInfo].account_id
    regions = ",".join(ctx.attr.deployment_zone[DeploymentZoneInfo].subnet_ids.keys())
    script = ctx.actions.declare_file(ctx.label.name + ".sh")
    script_content = "\n".join([
        "#!/bin/sh",
        "echo \"The deployment package path is {path}\"".format(path = package_path),
        "echo \"The deployment package is implemented in {language}\"".format(language = language),
        "echo \"The deployment will create infrastructure in account: {account_id}\"".format(account_id = account),
        "echo \"The deployment will create infrastructure in regions: {regions}\"".format(regions = regions),
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
        "deployment_zone": attr.label(
            providers = [DeploymentZoneInfo],
            mandatory = True,
        ),
        "package": attr.label(
            providers = [PackageInfo],
            mandatory = True,
        ),
    },
    executable = True,
)
