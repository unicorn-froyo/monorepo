"""Get Widgets API"""
from http import HTTPStatus

from src.apis.abstract_api_base import AbstractApiBase


class GetWidgets(AbstractApiBase):  # pylint: disable = too-few-public-methods
    """Test Endpoint"""

    def __init__(
        self, *args, **kwargs
    ):  # pylint: disable = useless-super-delegation
        """Constructor Method"""
        super().__init__(*args, **kwargs)

    def execute(
        self, request: dict  # pylint: disable = unused-argument
    ) -> dict:
        """Entrypoint into Lambda Function

        Args:
            request (dict): Api Gateway Event

        Returns:
            dict: API Gateway compatible response
        """

        return self.response(message="", status_code=HTTPStatus.ACCEPTED.value)


def handler(event: dict, context: object) -> dict:
    """API handler function

    Args:
        event (dict): API Gateway Event
        context (object): AWS Lambda Context Object

    Returns:
        dict: API Gateway compatible response
    """
    return GetWidgets().get_aws_lambda_handler()(event=event, context=context)
