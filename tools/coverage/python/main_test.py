from unittest import TestCase, main
from unittest.mock import patch

from tools.coverage.python.main import print_hello

class TestMain(TestCase):

    @patch('builtins.print')
    def test_print_hello(self, mock_print):
        print_hello()

        mock_print.assert_called_once_with("hello")


