"""Dependency checks and conservative package-manager synchronization.

Ordinary tests validate declared direct requirements against checked-in lock
metadata. Only explicit check/update commands contact package registries.
"""

import base64
import difflib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import tomllib
from pathlib import Path

LOCKS = {
    "golang": ["go.mod", "go.sum"],
    "npm": ["pnpm-lock.yaml"],
    "ruby": ["Gemfile.lock"],
    "rust": ["dependencies.Cargo.lock"],
}


def run(args, cwd, env, capture=False):
    return subprocess.run(
        [str(arg) for arg in args],
        cwd=cwd,
        env=env,
        check=True,
        text=True,
        stdout=subprocess.PIPE if capture else None,
    ).stdout


def stage(language, inputs, destination):
    """Copy writable inputs; Go sources must share the staged module root."""
    prefix = f"third_party/{language}/"
    for relative, source in inputs.items():
        target = destination / (
            relative.removeprefix(prefix) if relative.startswith(prefix) else relative
        )
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, target)
    if language == "rust":
        (destination / "dependencies.Cargo.lock").rename(destination / "Cargo.lock")


def check_go(directory, tools, env):
    manifest = json.loads(run([tools["go"], "mod", "edit", "-json"], directory, env, True))
    if not manifest.get("Module", {}).get("Path"):
        raise ValueError("go.mod must declare a module")
    sums = set()
    for line in (directory / "go.sum").read_text().splitlines():
        module, version, checksum = line.split()
        if (
            not checksum.startswith("h1:")
            or len(base64.b64decode(checksum[3:], validate=True)) != 32
        ):
            raise ValueError(f"Invalid go.sum hash: {line}")
        sums.add((module, version.removesuffix("/go.mod")))
    for requirement in manifest.get("Require", []):
        if (requirement["Path"], requirement["Version"]) not in sums:
            raise ValueError(
                f"Missing go.sum entry for {requirement['Path']} {requirement['Version']}"
            )


def check_npm(directory, tools, env):
    manifest = json.loads((directory / "package.json").read_text())
    lock = json.loads(run([tools["yq"], "-o=json", ".", "pnpm-lock.yaml"], directory, env, True))
    if str(lock.get("lockfileVersion")) not in ("9", "9.0"):
        raise ValueError("Expected pnpm lockfile version 9")
    importer = lock["importers"]["."]
    for group in ("dependencies", "devDependencies", "optionalDependencies"):
        required = manifest.get(group, {})
        locked = importer.get(group, {})
        if set(required) != set(locked):
            raise ValueError(f"pnpm {group} differs from package.json")
        for name, specifier in required.items():
            record = locked[name]
            if record["specifier"] != specifier:
                raise ValueError(f"pnpm requirement differs for {name}")
            package = f"{name}@{record['version'].split('(')[0]}"
            if package not in lock.get("packages", {}):
                raise ValueError(f"pnpm resolution missing for {package}")


RUBY_CHECK = """
require "bundler"
definition = Bundler::Definition.build("Gemfile", "Gemfile.lock", nil)
definition.ensure_equivalent_gemfile_and_lockfile(true)
locked = Bundler::LockfileParser.new(File.read("Gemfile.lock"))
definition.dependencies.each do |dependency|
  unless locked.specs.any? { |spec| dependency.matches_spec?(spec) }
    abort "No locked gem satisfies #{dependency}"
  end
end
"""


def rust_requirement_matches(version, requirement):
    """Check Cargo's numeric caret/tilde/exact/range/wildcard requirements.

    Fail explicitly for prereleases, operator/wildcard combinations, or other
    unsupported syntax instead of accepting a lock without validation.
    """
    if not re.fullmatch(r"\d+\.\d+\.\d+", version):
        raise ValueError(f"Unsupported Cargo prerelease/version: {version}")
    actual = tuple(map(int, version.split(".")))
    for part in requirement.split(","):
        match = re.fullmatch(
            r"\s*(>=|<=|>|<|=|\^|~)?\s*(\d+|\*)(?:\.(\d+|\*))?(?:\.(\d+|\*))?\s*", part
        )
        if not match:
            raise ValueError(f"Unsupported Cargo requirement: {requirement}")
        operator, *components = match.groups()
        if "*" in components:
            first_wildcard = components.index("*")
            if (
                operator is not None
                or any(
                    component not in (None, "*") for component in components[first_wildcard + 1 :]
                )
                or (first_wildcard == 0 and requirement.strip() != "*")
            ):
                raise ValueError(f"Unsupported Cargo wildcard requirement: {requirement}")
        numeric = []
        for component in components:
            if component in (None, "*"):
                break
            numeric.append(int(component))
        if not numeric:
            continue
        lower = tuple(numeric + [0] * (3 - len(numeric)))
        if operator in (">", ">=", "<", "<=", "="):
            # Cargo compares only specified components: >1.2 excludes all
            # 1.2.x versions, while <=1.2 includes them. Padding with zero
            # would incorrectly turn those into >1.2.0 and <=1.2.0.
            prefix = actual[: len(numeric)]
            requested = tuple(numeric)
            matches = {
                ">": prefix > requested,
                ">=": prefix >= requested,
                "<": prefix < requested,
                "<=": prefix <= requested,
                "=": prefix == requested,
            }[operator]
        else:
            if "*" in components or operator == "~":
                pivot = min(len(numeric) - 1, 1) if operator == "~" else len(numeric) - 1
            else:
                pivot = next((i for i, value in enumerate(numeric) if value), len(numeric) - 1)
            upper = list(lower)
            upper[pivot] += 1
            upper[pivot + 1 :] = [0] * (2 - pivot)
            matches = lower <= actual < tuple(upper)
        if not matches:
            return False
    return True


def check_rust(directory):
    manifest = tomllib.loads((directory / "Cargo.toml").read_text())
    lock = tomllib.loads((directory / "Cargo.lock").read_text())
    if lock.get("version") != 4:
        raise ValueError("Expected Cargo lockfile version 4")
    packages = lock["package"]
    roots = [p for p in packages if p["name"] == manifest["package"]["name"]]
    if len(roots) != 1 or roots[0]["version"] != manifest["package"]["version"]:
        raise ValueError("Cargo manifest package does not match lockfile")
    requirements = manifest.get("dependencies", {})
    direct_names = {
        value.get("package", name) if isinstance(value, dict) else name
        for name, value in requirements.items()
    }
    if direct_names != {dependency.split()[0] for dependency in roots[0].get("dependencies", [])}:
        raise ValueError("Cargo direct dependency names differ from lockfile")
    references = {}
    for package in packages:
        resolved = {}
        for dependency in package.get("dependencies", []):
            components = dependency.split()
            candidates = [p for p in packages if p["name"] == components[0]]
            if len(components) > 1:
                candidates = [p for p in candidates if p["version"] == components[1]]
            if len(components) > 2:
                candidates = [p for p in candidates if p.get("source") == components[2].strip("()")]
            if len(candidates) != 1:
                raise ValueError(f"Missing or ambiguous Cargo lock reference: {dependency}")
            resolved[components[0]] = candidates[0]
        if package is roots[0]:
            references = resolved
    for name, value in requirements.items():
        name, requirement = (
            (value.get("package", name), value["version"])
            if isinstance(value, dict)
            else (name, value)
        )
        if not rust_requirement_matches(references[name]["version"], requirement):
            raise ValueError(f"No locked Cargo package satisfies {name} {requirement}")
    for package in packages:
        if package.get("source", "").startswith("registry+") and not re.fullmatch(
            r"[a-f0-9]{64}", package.get("checksum", "")
        ):
            raise ValueError(f"Missing/invalid Cargo checksum for {package['name']}")


def synchronize(language, directory, tools, env):
    """Preserve compatible existing pins; this is synchronization, not upgrade."""
    if language == "golang":
        run([tools["go"], "mod", "tidy"], directory, env)
    elif language == "npm":
        # This is a runtime invocation rather than a Bazel build action.
        env = dict(env, BAZEL_BINDIR=".")
        run(
            [
                tools["pnpm"],
                "--dir",
                directory,
                "install",
                "--lockfile-only",
                "--ignore-scripts",
                "--no-frozen-lockfile",
            ],
            directory,
            env,
        )
    elif language == "ruby":
        bundler = tools["bundler"] / "gems/bundler-2.6.9"
        run([tools["ruby"], "-I", bundler / "lib", bundler / "exe/bundle", "lock"], directory, env)
    else:
        run([tools["cargo"], "update", "--workspace"], directory, env)


def collect_outputs(language, directory):
    return {
        name: (directory / ("Cargo.lock" if language == "rust" else name)).read_bytes()
        for name in LOCKS[language]
    }


def apply_outputs(language, outputs, inputs, workspace, update):
    """Never write any workspace file until resolution has succeeded."""
    different = False
    for name, content in outputs.items():
        relative = f"third_party/{language}/{name}"
        previous = inputs[relative].read_bytes()
        if previous == content:
            continue
        different = True
        print(
            "".join(
                difflib.unified_diff(
                    previous.decode().splitlines(True),
                    content.decode().splitlines(True),
                    fromfile=relative,
                    tofile=relative + " (resolved)",
                )
            )
        )
    if different and not update:
        raise ValueError(
            "Dependency lock files differ; run this ecosystem's dependencies.update target"
        )
    if update:
        for name, content in outputs.items():
            (workspace / f"third_party/{language}/{name}").write_bytes(content)


def main():
    config = json.loads(Path(sys.argv[1]).read_text())
    language, mode = config["language"], config["mode"]
    inputs = {relative: Path(relative).absolute() for relative in config["inputs"]}
    tools = {name: Path(value).absolute() for name, value in config["tools"].items()}
    workspace = Path(os.environ["BUILD_WORKSPACE_DIRECTORY"]) if mode == "update" else None
    with tempfile.TemporaryDirectory(prefix="dependency-maintenance-") as temporary:
        scratch = Path(temporary)
        directory = scratch / "project"
        directory.mkdir()
        stage(language, inputs, directory)
        env = {
            key: value
            for key, value in os.environ.items()
            if key
            not in (
                "GOFLAGS",
                "GOWORK",
                "GOTOOLCHAIN",
                "GOROOT",
                "GOPATH",
                "GOMODCACHE",
                "CARGO_HOME",
                "RUSTC",
                "RUSTUP_HOME",
            )
            and not key.startswith(("BUNDLE_", "GEM_"))
        }
        env.update(config.get("env", {}))
        env.update(
            {
                "HOME": str(scratch),
                "GOTOOLCHAIN": "local",
                "GOWORK": "off",
                "GOPATH": str(scratch / "go"),
                "GOCACHE": str(scratch / "go-build"),
                "CARGO_HOME": str(scratch / "cargo"),
                "BUNDLE_IGNORE_CONFIG": "true",
                "XDG_CACHE_HOME": str(scratch / "cache"),
                "XDG_DATA_HOME": str(scratch / "data"),
                "XDG_CONFIG_HOME": str(scratch / "config"),
                "PNPM_HOME": str(scratch / "pnpm"),
                "npm_config_cache": str(scratch / "npm-cache"),
            }
        )
        if "goroot" in tools:
            env["GOROOT"] = str(tools["goroot"].parent)
        if "rustc" in tools:
            env["RUSTC"] = str(tools["rustc"])
        if mode == "test":
            env.update({"GOPROXY": "off", "GOSUMDB": "off", "CARGO_NET_OFFLINE": "true"})
            if language == "golang":
                check_go(directory, tools, env)
            elif language == "npm":
                check_npm(directory, tools, env)
            elif language == "ruby":
                run([tools["ruby"], "-e", RUBY_CHECK], directory, env)
            else:
                check_rust(directory)
            print(f"{language}: offline direct requirement / lock metadata checks passed")
        else:
            synchronize(language, directory, tools, env)
            apply_outputs(
                language, collect_outputs(language, directory), inputs, workspace, mode == "update"
            )
            print(f"{language}: dependency {mode} succeeded")


if __name__ == "__main__":
    try:
        main()
    except (ValueError, KeyError, subprocess.CalledProcessError) as error:
        print(f"Dependency maintenance failed: {error}", file=sys.stderr)
        sys.exit(1)
