"""Get Widgets API tests"""
import logging
import json
from unittest import TestCase, main
from unittest.mock import Mock
from src.apis.examples.get_widgets import handler


class TestGetWidgets(TestCase):
    """Get Widgets API tests"""

    maxDiff = None

    class Context:  # pylint: disable=too-few-public-methods
        """."""

        function_name = "test-function"
        function_version = "$LATEST"

    event = {
        "resource": "/",
        "path": "/",
        "httpMethod": "POST",
        "headers": {
            "Accept": (
                "text/html,application/xhtml+xml,application/xml;"
                "q=0.9,image/webp,image/apng,*/*;q=0.8"
            ),
            "Accept-Encoding": "gzip, deflate, br",
        },
        "queryStringParameters": None,
        "pathParameters": None,
        "stageVariables": None,
        "requestContext": {
            "path": "/dev/",
            "accountId": "125002137610",
            "resourceId": "qdolsr1yhk",
            "stage": "dev",
            "requestId": "0f2431a2-6d2f-11e7-b799-5152aa497861",
            "identity": {
                "cognitoIdentityPoolId": None,
                "accountId": None,
                "cognitoIdentityId": None,
                "caller": None,
                "apiKey": "",
                "sourceIp": "50.129.117.14",
                "accessKey": None,
                "cognitoAuthenticationType": None,
                "cognitoAuthenticationProvider": None,
                "userArn": None,
                "userAgent": (
                    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_12_5) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/59"
                    ".0.3071.115 Safari/537.36"
                ),
                "user": None,
            },
            "resourcePath": "/",
            "httpMethod": "POST",
            "apiId": "j3azlsj0c4",
        },
        "body": f"{json.dumps({})}",
        "isBase64Encoded": False,
    }

    def test_handler(self):
        """Test GetWidgets Handler function."""
        logging_mock = logging.info = Mock()
        response = handler(self.event, self.Context())
        logging_mock.assert_not_called()
        self.assertDictEqual(
            response,
            {
                "body": '""',
                "headers": {"Content-Type": "application/json"},
                "statusCode": 202,
            },
        )


if __name__ == "__main__":
    main(verbosity=2)
