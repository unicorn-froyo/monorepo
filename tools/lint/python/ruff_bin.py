"""Entrypoint for the Ruff executable bundled in its pinned wheel."""

import os
import sys
from pathlib import Path

import ruff

if __name__ == "__main__":
    # rules_python unpacks wheel scripts into bin/, not the host virtualenv.
    binary = Path(ruff.__file__).resolve().parents[2] / "bin" / "ruff"
    os.execv(binary, ["ruff", *sys.argv[1:]])
