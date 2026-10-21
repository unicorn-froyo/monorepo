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

Python, Ruby, and TypeScript coverage targets run during `bazelisk test //...`.
Ruby and TypeScript LCOV reports are saved in each coverage target's
`bazel-testlogs/<package>/<target>/test.outputs/lcov.info`.

Go and Rust use Bazel's coverage command; their `*_coverage_test` suites select
the existing unit tests without building duplicate test binaries:

```bash
bazelisk coverage --combined_report=lcov --instrumentation_filter='//src/apis[/:]' \
  //src/apis/go:api_base_go_coverage_test \
  //src/apis/examples/go:get_widgets_example_go_coverage_test \
  //src/apis/rust:api_base_rs_coverage_test \
  //src/apis/examples/rust:get_widgets_example_rs_coverage_test
```

The combined Go/Rust LCOV report is `bazel-out/_coverage/_coverage_report.dat`.
Coverage is reported without imposing a new minimum-percentage policy.
