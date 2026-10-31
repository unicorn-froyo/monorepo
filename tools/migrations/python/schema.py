"""Validate Flyway source contracts and lint every declared SQL file offline."""

import argparse
import json
import re
import sys
from pathlib import Path

from sqlfluff.core import FluffConfig, Linter

NAME = re.compile(r"V([0-9]+(?:[._][0-9]+)*)__([a-z][a-z0-9_]*)\.sql\Z")
IDENTIFIER = re.compile(r"[a-z][a-z0-9_]*\Z")


def validate(bundle: dict) -> list[Path]:
    """Check names and supported configuration without a database or credentials."""
    for key in ("schema", "history_table"):
        if not IDENTIFIER.fullmatch(bundle[key]):
            raise ValueError(f"{key}: expected a lowercase SQL identifier")
    paths = [Path(value) for value in bundle["sql_files"]]
    if not paths:
        raise ValueError("No migration SQL files declared")
    versions = set()
    names = set()
    for path in paths:
        match = NAME.fullmatch(path.name)
        if not match:
            raise ValueError(f"{path}: expected V<version>__<description>.sql")
        version = tuple(int(part) for part in re.split(r"[._]", match[1]))
        # Flyway treats leading/trailing zero components as equivalent versions.
        while len(version) > 1 and version[-1] == 0:
            version = version[:-1]
        if version in versions:
            raise ValueError(f"{path}: duplicate migration version")
        versions.add(version)
        names.add(path.name)
        if not path.read_text().strip():
            raise ValueError(f"{path}: empty migration")
        if "${" in path.read_text():
            raise ValueError(f"{path}: Flyway placeholders are disabled")
    configs = set()
    for value in bundle["script_configs"]:
        path = Path(value)
        if path.name.removesuffix(".conf") not in names or path.name in configs:
            raise ValueError(f"{path}: orphan or duplicate script configuration")
        configs.add(path.name)
        if path.read_text().strip() not in (
            "executeInTransaction=false",
            "executeInTransaction=true",
        ):
            raise ValueError(f"{path}: only executeInTransaction=true/false is supported")
    return paths


def lint(bundle: dict, config: Path) -> list[str]:
    """Use explicit config and literal SQL so developer config cannot skip files."""
    paths = validate(bundle)
    settings = FluffConfig.from_string(config.read_text())
    settings.set_value(["core", "dialect"], "postgres")
    settings.set_value(["core", "templater"], "raw")
    settings.set_value(["core", "large_file_skip_byte_limit"], 0)
    settings.set_value(["core", "large_file_skip_char_limit"], 0)
    linter = Linter(config=settings)
    errors = []
    for path in paths:
        result = linter.lint_string(path.read_text(), fname=str(path))
        # Ignore inline noqa directives: syntax and style policy apply to all SQL.
        for violation in result.get_violations(filter_ignore=False):
            errors.append(
                f"{path}:{violation.line_no}:{violation.line_pos}: "
                f"{violation.rule_code()}: {violation.desc()}"
            )
    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--config", type=Path, required=True)
    args = parser.parse_args()
    try:
        errors = lint(json.loads(args.manifest.read_text()), args.config)
        for error in errors:
            print(error, file=sys.stderr)
        return int(bool(errors))
    except (OSError, ValueError, KeyError) as error:
        print(f"Schema validation failed: {error}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
