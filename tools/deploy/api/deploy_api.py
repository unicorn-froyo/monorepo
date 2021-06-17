"""API Packaging Binary for package_api rule
"""
import json
from argparse import ArgumentParser
from textwrap import dedent
from typing import Any, List

# custom
import boto3
from botocore.exceptions import ClientError


class DeployApi:  # pylint: disable=too-few-public-methods
    """Deployment runner for Api Deployment Types"""

    _EMPTY_STACK = json.dumps(
        {
            "AWSTemplateFormatVersion": "2010-09-09",
            "Description": "Initial stack",
            "Resources": {
                "Wait": {
                    "Type": "AWS::CloudFormation::WaitConditionHandle",
                    "Properties": {},
                }
            },
        }
    )

    def __init__(self, properties: dict, profile: str):
        """Constructor Method

        Args:
            args (Namespace): Parsed Arguments
        """
        self.properties = properties
        self.sessions = []
        for region in json.loads(self.properties["SubnetIds"]).keys():
            self.sessions.append(
                boto3.session.Session(profile_name=profile, region_name=region)
            )

    def deploy_package_hosting(self):
        """Deploy the package hosting stack for Lambda functions"""
        # waiters = []
        template = ""
        with open(self.properties["PackageHostingTemplate"], "r") as file:
            template = file.read()

        for session in self.sessions:
            client = session.client("cloudformation")
            stack_name = f"{self.properties['AccountId']}{session.region_name}.packages.clearme.com"
            self.deploy_stack(
                client=client,
                stack_name=stack_name,
                template_body=template,
                parameters=[
                    {
                        "ParameterKey": "BucketName",
                        "ParameterValue": stack_name,
                    },
                    {
                        "ParameterKey": "DeploymentRole",
                        "ParameterValue": self.properties["DeploymentRole"],
                    },
                    {
                        "ParameterKey": "OwnerRole",
                        "ParameterValue": self.properties["OwnerRole"],
                    },
                ],
                tags=[
                    {
                        "Key": "OwnerContact",
                        "Value": self.properties["OwnerContact"],
                    },
                ],
            )

    def deploy_stack(
        self,
        client: Any,
        stack_name: str,
        template_body: str,
        parameters: List[dict],
        tags: List[dict],
    ):
        # try:
        client.update_stack(
            StackName=stack_name,
            TemplateBody=template_body,
            Parameters=parameters,
            Tags=tags,
        )

    # except ClientError:
    #     pass

    def deploy(self) -> None:
        """Deployment entrypoint"""

        waiters = self.deploy_package_hosting()
        if waiters:
            for waiter in waiters:
                waiter.wait()


if __name__ == "__main__":
    parser = ArgumentParser(
        description=dedent(
            """The deployment script for API deployment types.
    """
        ),
        add_help=True,
    )
    parser.add_argument(help="Deployment Type Properties", dest="properties")
    parser.add_argument(
        "--profile",
        default=None,
        help="Profile to assume",
    )
    args = parser.parse_args()
    DeployApi(
        properties=json.loads(args.properties), profile=args.profile
    ).deploy()
