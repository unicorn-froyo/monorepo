"""Deployment rules
"""

load("//tools:providers.bzl", "DeploymentZoneInfo")

def _deployment_zone_impl(ctx):
    if len(ctx.attr.account_id) != 12:
        fail("AWS Account IDs are 12 characters long")
    return [
        DeploymentZoneInfo(
            account_id = ctx.attr.account_id,
            deployment_role = ctx.attr.deployment_role,
            owner_contact = ctx.attr.owner_contact,
            owner_role = ctx.attr.owner_role,
            subnet_ids = ctx.attr.subnet_ids,
        ),
    ]

deployment_zone = rule(
    implementation = _deployment_zone_impl,
    attrs = {
        "account_id": attr.string(doc = "The AWS Account ID.", mandatory = True),
        "deployment_role": attr.string(doc = "The IAM Role used in deployment.", mandatory = True),
        "owner_contact": attr.string(doc = "The contact information assocaited with this infra.", mandatory = True),
        "owner_role": attr.string(doc = "The IAM Role used by support teams.", mandatory = True),
        "subnet_ids": attr.string_list_dict(doc = "The AWS Subnets where application infrastructure will be deployed.", mandatory = True),
    },
)
