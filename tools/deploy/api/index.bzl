"""Rules for deploying a containerized API."""

load("//tools:providers.bzl", "DeploymentZoneInfo")

def _deploy_api_impl(ctx):
    account = ctx.attr.deployment_zone[DeploymentZoneInfo].account_id
    regions = ",".join(ctx.attr.deployment_zone[DeploymentZoneInfo].subnet_ids.keys())
    script = ctx.actions.declare_file(ctx.label.name + ".sh")
    script_content = "\n".join([
        "#!/bin/sh",
        "echo \"The deployment image is {image}\"".format(image = ctx.attr.image_name),
        "echo \"The deployment will create infrastructure in account: {account_id}\"".format(account_id = account),
        "echo \"The deployment will create infrastructure in regions: {regions}\"".format(regions = regions),
    ])

    ctx.actions.write(script, script_content, is_executable = True)

    return [DefaultInfo(executable = script)]

deploy_api = rule(
    implementation = _deploy_api_impl,
    attrs = {
        "deployment_zone": attr.label(
            providers = [DeploymentZoneInfo],
            mandatory = True,
        ),
        "image": attr.label(mandatory = True),
        "image_name": attr.string(mandatory = True),
    },
    executable = True,
)
