"""Testing: Packaging module used within package_api bazel rule"""

from unittest import TestCase, main
from unittest.mock import call, patch

from tools.package.package_bin import Package


class TestPackage(TestCase):
    """Testing: Packaging module used within package_api bazel rule"""

    maxDiff = None

    class Namespace:  # pylint: disable=too-few-public-methods
        """."""

        files = None
        runtime = None
        output_file = None

    def test_raises_value_error(self):
        """Test raises ValueError"""
        args = self.Namespace()
        with self.assertRaises(ValueError) as ctx:
            Package(args=args).execute()
        self.assertEqual(ctx.exception.args[0], "No files were supplied")

    def test_raises_not_implemented_error(self):
        """Test raises NotImplementedError"""
        args = self.Namespace()
        args.files = "file1,file2"
        args.runtime = "not supported"
        with self.assertRaises(NotImplementedError) as ctx:
            Package(args=args).execute()
        self.assertEqual(
            ctx.exception.args[0], "Only python is supported at this time"
        )

    @patch("os.stat")
    @patch("tools.package.package_bin.ZipFile")
    def test_success(self, zip_mock, mock_stat):
        """Test raises NotImplementedError"""
        args = self.Namespace()
        args.files = "file1,file2"
        args.runtime = "python"
        args.output_file = "output-file.zip"
        mock_stat.return_value.st_size = 35
        mock_stat.return_value.st_mode = 15
        mock_stat.return_value.st_mtime = 1565355651
        Package(args=args).execute()
        zip_mock.assert_called_with("output-file.zip", "w")
        zip_mock.return_value.__enter__().write.assert_has_calls(
            [call("file1"), call("file2")]
        )


if __name__ == "__main__":
    main(verbosity=2)
