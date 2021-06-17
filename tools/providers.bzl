"""Tools Providers"""

PackageInfo = provider(
    doc = "This provider contains package information",
    fields = {"language": "The language environment of the package."},
)

DeploymentZoneInfo = provider(
    doc = "The the template of a code deployment location or zone. This is designed to be an AWS Account.",
    fields = {
        "account_id": "The AWS Account ID.",
        "deployment_role": "The IAM Role used in the Deployments.",
        "owner_contact": "The team who owns this infrastructure.",
        "owner_role": "The Support Role Assigned to the Development Team.",
        "subnet_ids": "The list of subnets in which code will be deployed.",
    },
)
