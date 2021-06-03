import os
from argparse import ArgumentParser, Namespace
from enum import Enum
from textwrap import dedent
from zipfile import ZipFile, ZIP_DEFLATED


class LambdaRuntimes(Enum):
    python = "python"
    nodejs = "nodejs"
    go = "go"

    @classmethod
    def values(cls):
        return list(map(lambda c: c.value, cls))


class Package:
    def __init__(self, args: Namespace):
        """Constructor Method

        Args:
            args (Namespace): Parsed Arguments
        """
        self.files = args.files.split(",") if args.files else args.files
        self.runtime = args.runtime
        self.output_file = args.output_file

    def execute(self) -> None:
        if not self.files:
            raise ValueError("No files were supplied")
        if self.runtime != LambdaRuntimes.python.value:
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
        default=LambdaRuntimes.python.value,
        help="The runtime environment for the package.",
        choices=LambdaRuntimes.values(),
    )
    parser.add_argument(
        "-",
        "--output-file",
        help="The path to set the package.",
    )
    Package(args=parser.parse_args()).execute()
