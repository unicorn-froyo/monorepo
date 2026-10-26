"""Run the pinned Ruff formatter against workspace-relative paths."""

import os
import sys
from pathlib import Path

import ruff


def main() -> None:
    """Replace this process with Ruff's formatter."""
    workspace = Path(os.environ.get("BUILD_WORKSPACE_DIRECTORY", Path.cwd()))
    config = workspace / "tools/lint/python/ruff.toml"
    sources = [
        str(workspace / source) if not Path(source).is_absolute() else source
        for source in sys.argv[1:]
    ]
    binary = Path(ruff.__file__).resolve().parents[2] / "bin" / "ruff"
    os.execv(binary, ["ruff", "format", "--config", str(config), *sources])


if __name__ == "__main__":
    main()
