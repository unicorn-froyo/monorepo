"""Abstract API Base Class for API Deployment Types"""
import json
from abc import ABC, abstractmethod
from http import HTTPStatus
from typing import Union


class AbstractApiBase(ABC):
    """Api Base"""

    def __init__(self, *args, **kwargs):
        """Constructor Method"""
        super(*args, **kwargs)

    @abstractmethod
    def execute(self, request: dict) -> dict:
        """Abstract Execute Method"""

    @staticmethod
    def response(
        message: dict,
        status_code: int = HTTPStatus.OK.value,
        headers: Union[dict, None] = None,
    ) -> dict:
        """Standard response to API Gateway

        Args:
            message (dict): Response message as a dictionary.
            status_code (int, optional): Response Http Status Code. Defaults to HTTPStatus.OK.value.
            headers (Union[dict, None], optional): Response Headers. Defaults to None.

        Returns:
            dict: AWS API Gateway Response Dictionary
        """
        headers = (
            {"Content-Type": "application/json"}
            if headers is None
            else headers
        )
        return {
            "statusCode": status_code,
            "headers": headers,
            "body": json.dumps(message),
        }

    @classmethod
    def get_aws_lambda_handler(cls, *args, **kwargs):
        """Wrapper to return the AWS Lambda Handler function

        Returns:
            dict: Api Response dict
        """
        command = cls(*args, **kwargs)

        def handler(event, context):  # pylint: disable = unused-argument
            # pylint: disable = fixme
            # TODO: setup request using protobuf
            # TODO: read secrets
            # pylint: enable = fixme
            return command.execute(event)

        return handler
