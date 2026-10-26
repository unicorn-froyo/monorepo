"""Run Pyright against declared sources and Bazel-provided Python imports."""

import argparse
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pyright", required=True)
    parser.add_argument("--config", required=True)
    parser.add_argument("--imports-json", default="[]")
    parser.add_argument("sources", nargs="+")
    args = parser.parse_args()

    runfiles = Path(os.environ.get("RUNFILES_DIR") or os.environ["TEST_SRCDIR"])
    workspace = runfiles / os.environ.get("TEST_WORKSPACE", "_main")
    imports = [workspace, *(runfiles / path for path in json.loads(args.imports_json))]
    config = json.loads(Path(args.config).read_text())
    config["extraPaths"] = [str(path.absolute()) for path in imports]
    sources = [str(Path(source).absolute()) for source in args.sources]
    pyright = str(Path(args.pyright).absolute())
    with tempfile.TemporaryDirectory(
        prefix="pyright-", dir=os.environ.get("TEST_TMPDIR")
    ) as directory:
        config_path = Path(directory) / "pyrightconfig.json"
        config_path.write_text(json.dumps(config))
        # Probe the declared hermetic interpreter, never an ambient virtualenv.
        env = os.environ.copy()
        env.pop("PYTHONPATH", None)
        return subprocess.run(
            [pyright, "--pythonpath", sys.executable, "--project", str(config_path), *sources],
            env=env,
            check=False,
        ).returncode


if __name__ == "__main__":
    sys.exit(main())
