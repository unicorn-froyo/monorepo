# monorepo

## Description

This template repository implements a polyglot monorepository structure using [Bazel](https://www.bazel.build/) as the build tool.

## Principles

1. Builds are hermetic.
2. Commits are atomic.
3. APIs are portable HTTP applications, not cloud-function handlers.

## Supported API stacks

Python APIs use [FastAPI](https://fastapi.tiangolo.com/) and expose an ASGI
application. Ruby APIs use [Rails](https://rubyonrails.org/) in API-only mode and
expose a Rack application. Go APIs use [Gin](https://gin-gonic.com/), Rust APIs
use [Axum](https://github.com/tokio-rs/axum), and TypeScript APIs use
[Express](https://expressjs.com/).

APIs are distributed as OCI-compatible images composed from Bazel-built layers
with `rules_oci`. Image targets are tagged `manual`, keeping image loading out of
normal `bazelisk build //...` operations.

Build the examples from the repository root:

```bash
bazelisk run //src/apis/examples/go:get_widgets_example_image
bazelisk run //src/apis/examples/python:get_widgets_example_image
bazelisk run //src/apis/examples/ruby:get_widgets_example_image
bazelisk run //src/apis/examples/rust:get_widgets_example_image
bazelisk run //src/apis/examples/typescript:get_widgets_example_image
```

Run the resulting containers:

```bash
docker run --rm -p 8080:8080 get-widgets-go:latest
# or

docker run --rm -p 8080:8080 get-widgets-python:latest
# or

docker run --rm -p 8080:8080 get-widgets-ruby:latest
# or

docker run --rm -p 8080:8080 get-widgets-rust:latest
# or

docker run --rm -p 8080:8080 get-widgets-typescript:latest
```

All examples serve `GET /widgets` on port 8080.

All supported API stacks follow the [cross-platform API standards](src/apis/STANDARDS.md),
including consistent security headers on HTTP responses and HTTPS-only HSTS.

## Supported languages

Go, Python, Ruby, Rust, and TypeScript have hermetic Bazel toolchains. Use
`go_*` rules from `rules_go`, `py_*` rules from `rules_python`, `rb_*` rules from
`rules_ruby`, `rust_*` rules from `rules_rust`, and `ts_project` from
`aspect_rules_ts`. Go dependencies are locked under `third_party/golang`, Python dependencies
in `third_party/pypi/requirements.txt`, Ruby dependencies in
`third_party/ruby/Gemfile.lock`, Rust dependencies under `third_party/rust`, and
TypeScript dependencies under `third_party/npm`.

## Dependency maintenance

Go, npm, Ruby, and Rust expose the same maintenance targets under their
`third_party` package (`golang`, `npm`, `ruby`, or `rust`):

```bash
# Fast, offline manifest/direct-lock consistency checks; included in test //....
bazelisk test //third_party/golang:dependencies.test

# Run the package manager in scratch, failing with a diff if synchronization
# changes a lock. May contact registries; never writes workspace files.
bazelisk run //third_party/golang:dependencies.check

# Synchronize the checked-in lock files after editing the manifest.
bazelisk run //third_party/golang:dependencies.update
```

The update and check commands use Bazel's language toolchains and existing locks,
preserving compatible versions. They do not request a blanket dependency upgrade.
All package-manager writes and caches stay in a temporary directory until an
update succeeds. Only the ecosystem's declared lock outputs are copied back;
Go also copies back `go.mod` because `go mod tidy` maintains indirect requirements.
The npm runner uses pnpm from `package.json#packageManager`; Ruby maintenance uses
Bundler 2.6.9 from `Gemfile.lock` (update its tool label when changing Bundler).
No globally installed package managers are used.

The offline tests have a deliberately narrower guarantee than a resolver run:

- Go parses `go.mod` with the SDK and checks that each required module/version
  has a structurally valid `go.sum` entry. It does not verify downloaded content
  or whether the import graph is tidy. The full commands stage both API Go
  source packages alongside `go.mod`; add new Go packages to that source list.
- npm checks pnpm v9 lock metadata, direct dependency names/specifiers, and their
  package records against `package.json`.
- Ruby uses Bundler's Gemfile/lock equivalence check and verifies that each direct
  gem requirement has a matching locked specification, without installing gems.
- Rust checks the synthetic dependency manifest's direct names and numeric
  version requirements, package references, and checksum metadata against
  `dependencies.Cargo.lock`. Unsupported prerelease/version syntax fails explicitly.
  These checks do not re-resolve features or validate downloaded crate contents.

Use the explicit `.check` command for package-manager synchronization validation.
It permits registry access and starts with empty scratch caches, avoiding implicit
host-cache dependencies. Rust maintenance only owns `dependencies.Cargo.lock`;
the separate `Cargo.lock` used by the current example container is unchanged.
Python retains its existing `requirements.update` and `requirements.test` workflow:
edit `third_party/pypi/requirements.in`, then run
`bazelisk run //third_party/pypi:requirements.update`.

## How-to

### Install Bazel

Install [Bazelisk](https://github.com/bazelbuild/bazelisk) to manage the Bazel
version used by the workspace. On macOS:

```bash
brew install bazelisk openssl
```

### Build

```bash
bazelisk build //...
```

### Test

```bash
bazelisk test //...
```

### Lint and coverage

Lint checks run as part of the normal build/test workflow:

| Language | Lint tool | Coverage tool |
| --- | --- | --- |
| Go | SDK analyzers via `go_lint` (nogo, checked during builds) | Native `rules_go` instrumentation |
| Python | Ruff via `py_lint_test` | coverage.py via `py_coverage_test` |
| Ruby | RuboCop via `rb_lint_test` | SimpleCov via `rb_coverage_test` |
| Rust | Clippy and rustfmt via `rs_lint_test` | Native LLVM instrumentation via `rules_rust` |
| TypeScript | ESLint via `ts_lint_test` | c8/V8 via `ts_coverage_test`, mapped to TypeScript sources |

Reusable wrappers live under `tools/lint/<language>/index.bzl` and
`tools/coverage/<language>/index.bzl`. Dependencies are pinned in the ecosystem
lockfiles under `third_party/`; no globally installed linters are required.

All languages' coverage targets run during `bazelisk test //...` and are
discoverable as test rules (not just test suites). Go and Rust coverage rules
build their existing unit-test targets with instrumentation enabled via a
configuration transition, then run and collect coverage without requiring a
separate `bazel coverage` invocation.

Go, Ruby, Rust, and TypeScript LCOV reports are saved in each coverage target's
`bazel-testlogs/<package>/<target>/test.outputs/lcov.info`. Go also preserves its
native block profile as `test.outputs/coverage.out`.

All languages enforce **100% aggregate line coverage per target**, with the
minimum configured once in `tools/coverage/config.bzl`. Python additionally
measures branch coverage via `tools/coverage/python/.coveragerc`.
Reports are preserved even when the threshold fails. The shared line-coverage
minimum does not impose a branch/function threshold.
