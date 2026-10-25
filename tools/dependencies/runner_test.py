"""Exercise dependency drift and scratch/write boundaries without registries."""

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from tools.dependencies.runner import (
    apply_outputs,
    check_go,
    check_npm,
    check_rust,
    collect_outputs,
    rust_requirement_matches,
    stage,
)


class DependencyWorkflowTest(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)

    def write(self, path, content):
        file = self.root / path
        file.parent.mkdir(parents=True, exist_ok=True)
        file.write_text(content)
        return file

    def test_go_stages_sources_beneath_module_root_without_changing_workspace(self):
        manifest = self.write("workspace/third_party/golang/go.mod", "module example.com/project\n")
        source = self.write("workspace/src/api/server.go", "package main\n")
        destination = self.root / "scratch"
        stage(
            "golang",
            {"third_party/golang/go.mod": manifest, "src/api/server.go": source},
            destination,
        )
        self.assertEqual((destination / "go.mod").read_text(), manifest.read_text())
        self.assertEqual((destination / "src/api/server.go").read_text(), "package main\n")
        (destination / "go.mod").write_text("changed")
        self.assertEqual(manifest.read_text(), "module example.com/project\n")

    def test_check_reports_drift_without_writing_and_update_only_writes_lock(self):
        workspace = self.root / "workspace"
        lock = self.write("workspace/third_party/npm/pnpm-lock.yaml", "old\n")
        manifest = self.write("workspace/third_party/npm/package.json", "{}\n")
        inputs = {"third_party/npm/pnpm-lock.yaml": lock}
        with self.assertRaisesRegex(ValueError, "Dependency lock files differ"):
            apply_outputs("npm", {"pnpm-lock.yaml": b"new\n"}, inputs, None, False)
        self.assertEqual(lock.read_text(), "old\n")
        apply_outputs("npm", {"pnpm-lock.yaml": b"new\n"}, inputs, workspace, True)
        self.assertEqual(lock.read_text(), "new\n")
        self.assertEqual(manifest.read_text(), "{}\n")

    def test_go_requires_checksum_for_declared_version(self):
        self.write(
            "go.sum", "example.com/lib v1.2.3 h1:AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA=\n"
        )
        manifest = {
            "Module": {"Path": "example.com/app"},
            "Require": [{"Path": "example.com/lib", "Version": "v1.2.3"}],
        }
        with patch("tools.dependencies.runner.run", return_value=json.dumps(manifest)):
            check_go(self.root, {"go": "unused"}, {})
            self.write(
                "go.sum", "example.com/lib v1.2.4 h1:AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA=\n"
            )
            with self.assertRaisesRegex(ValueError, "Missing go.sum entry"):
                check_go(self.root, {"go": "unused"}, {})

    def test_npm_rejects_changed_specifier_and_missing_resolution(self):
        self.write("package.json", json.dumps({"dependencies": {"express": "5.1.0"}}))
        lock = {
            "lockfileVersion": "9.0",
            "importers": {
                ".": {"dependencies": {"express": {"specifier": "5.1.0", "version": "5.1.0"}}}
            },
            "packages": {"express@5.1.0": {}},
        }
        with patch("tools.dependencies.runner.run", return_value=json.dumps(lock)):
            check_npm(self.root, {"yq": "unused"}, {})
            self.write("package.json", json.dumps({"dependencies": {"express": "5.2.0"}}))
            with self.assertRaisesRegex(ValueError, "requirement differs"):
                check_npm(self.root, {"yq": "unused"}, {})
        self.write("package.json", json.dumps({"dependencies": {"express": "5.1.0"}}))
        lock["packages"] = {}
        with patch("tools.dependencies.runner.run", return_value=json.dumps(lock)):
            with self.assertRaisesRegex(ValueError, "resolution missing"):
                check_npm(self.root, {"yq": "unused"}, {})

    def test_rust_semver_rejects_incompatible_minor_zero_major_and_prereleases(self):
        for version, requirement, expected in (
            ("0.8.9", "0.8.6", True),
            ("0.9.0", "0.8.6", False),
            ("0.0.4", "0.0.3", False),
            ("1.9.0", "1.2", True),
            ("1.3.0", "~1.2.3", False),
            ("1.2.8", "~1.2.3", True),
            ("1.2.8", "1.2.*", True),
            ("2.0.0", ">=1.0, <2.0", False),
            ("1.2.3", "=1.2.3", True),
            ("1.2.4", "=1.2.3", False),
        ):
            with self.subTest(version=version, requirement=requirement):
                self.assertEqual(rust_requirement_matches(version, requirement), expected)
        with self.assertRaisesRegex(ValueError, "Unsupported Cargo"):
            rust_requirement_matches("1.2.3-beta.1", "1.2")

    def test_rust_partial_comparators_compare_only_specified_components(self):
        for version, requirement, expected in (
            ("1.2.1", ">1.2", False),
            ("1.2.999", ">1.2", False),
            ("1.3.0", ">1.2", True),
            ("1.2.9", "<=1.2", True),
            ("1.3.0", "<=1.2", False),
            ("1.2.0", ">=1.2", True),
            ("1.1.999", ">=1.2", False),
            ("1.1.999", "<1.2", True),
            ("1.2.0", "<1.2", False),
            ("1.99.99", ">1", False),
            ("2.0.0", ">1", True),
            ("1.99.99", "<=1", True),
            ("2.0.0", "<=1", False),
            ("1.2.4", ">1.2.3", True),
            ("1.2.4", "<=1.2.3", False),
        ):
            with self.subTest(version=version, requirement=requirement):
                self.assertEqual(rust_requirement_matches(version, requirement), expected)

    def test_rust_checks_direct_requirements_and_preserves_distinct_runtime_lock(self):
        manifest = self.write(
            "source/Cargo.toml",
            '[package]\nname="api-dependencies"\nversion="0.0.0"\n[dependencies]\naxum="0.8.6"\n',
        )
        lock = self.write(
            "source/dependencies.Cargo.lock",
            'version=4\n[[package]]\nname="api-dependencies"\nversion="0.0.0"\ndependencies=["axum"]\n[[package]]\nname="axum"\nversion="0.8.9"\n',
        )
        runtime = self.write("source/Cargo.lock", "runtime lock\n")
        scratch = self.root / "scratch"
        stage(
            "rust",
            {
                "third_party/rust/Cargo.toml": manifest,
                "third_party/rust/dependencies.Cargo.lock": lock,
            },
            scratch,
        )
        check_rust(scratch)
        self.assertEqual(
            collect_outputs("rust", scratch), {"dependencies.Cargo.lock": lock.read_bytes()}
        )
        (scratch / "Cargo.toml").write_text(
            manifest.read_text().replace('axum="0.8.6"', 'axum="0.9.0"')
        )
        with self.assertRaisesRegex(ValueError, "No locked Cargo package"):
            check_rust(scratch)
        self.assertEqual(runtime.read_text(), "runtime lock\n")


if __name__ == "__main__":
    unittest.main()
