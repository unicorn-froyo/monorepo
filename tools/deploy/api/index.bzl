"""index.bzl provides the py_coverage_test rule"""

load("//tools:providers.bzl", "DeploymentZoneInfo", "PackageInfo")
load("//tools:utils.bzl", "get_transitive_deps")

LAMBDA_RUNTIME = {
    "python": "python3.8",
}

def _deploy_api_impl(ctx):
    _PROPERTIES = """'{{
    \"AccountId\": \"{account_id}\",
    \"ApiTemplate\": \"{api_template}\",
    \"DeploymentRole\": \"{deployment_role}\",
    \"OwnerRole\": \"{owner_role}\",
    \"OwnerContact\": \"{owner_contact}\",
    \"Package\": \"{package}\",
    \"PackageHostingTemplate\": \"{package_hosting_template}\",
    \"RuntimeEnvironment\": \"{runtime_environment}\",
    \"SubnetIds\": \"{subnet_ids}\"
}}'""".format(
        account_id = ctx.attr.deployment_zone[DeploymentZoneInfo].account_id,
        api_template = "TODO",
        deployment_role = ctx.attr.deployment_zone[DeploymentZoneInfo].deployment_role,
        owner_contact = ctx.attr.deployment_zone[DeploymentZoneInfo].owner_contact,
        owner_role = ctx.attr.deployment_zone[DeploymentZoneInfo].owner_role,
        package = ctx.files.package[0].short_path,
        package_hosting_template = ctx.files._package_hosting_template[0].short_path,
        runtime_environment = LAMBDA_RUNTIME[ctx.attr.package[PackageInfo].language],
        subnet_ids = str(ctx.attr.deployment_zone[DeploymentZoneInfo].subnet_ids).replace("\"", "\\\""),
    )

    package_path = ctx.files.package[0].short_path
    language = ctx.attr.package[PackageInfo].language
    regions = ",".join(ctx.attr.deployment_zone[DeploymentZoneInfo].subnet_ids.keys())
    script = ctx.actions.declare_file(ctx.label.name + ".sh")
    script_content = "\n".join([
        "#!/bin/sh",
        # "echo \"Properties: {properties}\"".format(properties = str(_PROPERTIES)),
        "{deploy_api_bin} {properties}".format(deploy_api_bin = ctx.executable._deploy_api_bin.short_path, properties = str(_PROPERTIES)),
    ])

    ctx.actions.write(script, script_content, is_executable = True)
    return [DefaultInfo(
        executable = script,
        runfiles = ctx.runfiles(
            files = [script] +
                    ctx.files.package +
                    ctx.files._deploy_api_bin +
                    ctx.files._package_hosting_template +
                    ctx.files._python_bin +
                    get_transitive_deps([ctx.attr._deploy_api_bin]),
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
        "_deploy_api_bin": attr.label(
            default = Label("//tools/deploy/api:deploy_api_bin"),
            executable = True,
            cfg = "exec",
        ),
        "_package_hosting_template": attr.label(
            default = Label("//tools/deploy:package_hosting_template"),
            allow_single_file = True,
        ),
        "_python_bin": attr.label(
            default = "@python_interpreter//:python_bin",
            executable = True,
            cfg = "exec",
            allow_files = True,
        ),
    },
    executable = True,
)
