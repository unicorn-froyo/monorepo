"""API Packaging Binary for package_api rule
"""
from argparse import ArgumentParser, Namespace
from textwrap import dedent
from zipfile import ZipFile

from tools.package.package_runtimes import LambdaRuntimes


class Package:  # pylint: disable=too-few-public-methods
    """Creates the lambda compatible package"""

    def __init__(self, args: Namespace):
        """Constructor Method

        Args:
            args (Namespace): Parsed Arguments
        """
        self.files = args.files.split(",") if args.files else args.files
        self.runtime = args.runtime
        self.output_file = args.output_file

    def execute(self) -> None:
        """Execute the packaging binary

        Raises:
            ValueError: Raises if the first positional argument is empty.
            NotImplementedError: Raises when not using python.
        """
        if not self.files:
            raise ValueError("No files were supplied")
        if self.runtime != LambdaRuntimes.PYTHON.value:
            raise NotImplementedError("Only python is supported at this time")

        with ZipFile(self.output_file, "w") as file:
            for src in self.files:
                file.write(src)


if __name__ == "__main__":
    parser = ArgumentParser(
        description=dedent(
            """This program is implemented to create a lambda function
            compatible zipfile. It currently only supports python.
    """
        ),
        add_help=True,
    )
    parser.add_argument(
        "files",
        default=None,
        help="A string list of file paths to include in the zipfile",
    )
    parser.add_argument(
        "-r",
        "--runtime",
        default=LambdaRuntimes.PYTHON.value,
        help="The runtime environment for the package.",
        choices=LambdaRuntimes.values(),
    )
    parser.add_argument(
        "-",
        "--output-file",
        help="The path to set the package.",
    )
    Package(args=parser.parse_args()).execute()
