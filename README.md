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
[NestJS](https://nestjs.com/) with its Express adapter.

APIs are distributed as OCI-compatible images composed from Bazel-built layers
with `rules_oci`. Compatible image targets are included in normal
`bazelisk build //...` operations. Loading an image into Docker requires
`bazelisk run` on its load target.

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

Build the Ruby image on a Linux worker matching the desired image architecture
(amd64 or arm64). Its Bazel bundle action compiles native gem extensions using
Ruby 4.0.7, matching the pinned runtime image. The image contains the installed
bundle at `/usr/local/bundle`; startup only executes Puma and performs no gem
installation. An explicit Ruby image build on macOS fails with a Linux platform
compatibility diagnostic. Normal builds and tests remain available on macOS.

The Rust image packages the Bazel-built server directly and starts without
running Cargo or downloading dependencies. Build its image on a Linux amd64 or
arm64 worker matching the intended image architecture. Image builds from macOS
and cross-compilation are unsupported; native Rust builds and tests still work
on macOS. Use the Bazel image and manual smoke-test targets to validate each
Linux image architecture on a matching native worker.

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
| Python | Ruff via `py_lint_test` and `py_format_test`; Pyright via `py_typecheck_test` | coverage.py via `py_coverage_test` |
| Ruby | RuboCop via `rb_lint_test`, `rb_format_test`, and `rb_format_bin`; Sorbet via `rb_typecheck_test` | SimpleCov line coverage via `rb_coverage_test` |
| Rust | Clippy via `rs_lint_test`; rustfmt via `rs_format_test` and `rs_format_bin` | Native LLVM instrumentation via `rules_rust` |
| TypeScript | ESLint via `ts_lint_test` | c8/V8 via `ts_coverage_test`, mapped to TypeScript sources |

Reusable wrappers live under `tools/lint/<language>/index.bzl` and
`tools/coverage/<language>/index.bzl`. Dependencies are pinned in the ecosystem
lockfiles under `third_party/`; no globally installed linters are required.

Python app and tooling sources are also checked with `ruff format --check` and
Pyright's standard checks for Python 3.14 during `bazelisk test //...`.
`py_typecheck_test` accepts Python `srcs` and declared `deps`; dependency import
paths come from Bazel's Python providers and Pyright uses the hermetic Python
interpreter. Pyright is pinned in the npm lockfile alongside the Node tooling.

Ruby sources use `# typed: true` and are checked by Sorbet through
`rb_typecheck_test` targets in the API, example, and coverage tooling packages.
Ruby OCI services use `rb_package` and `rb_image` to package Bazel-installed
gems; containers do not install gems at startup.

All languages' coverage targets run during `bazelisk test //...` and are
discoverable as test rules (not just test suites). Go and Rust coverage rules
build their existing unit-test targets with instrumentation enabled via a
configuration transition, then run and collect coverage without requiring a
separate `bazel coverage` invocation.

All languages' LCOV reports are saved in each coverage target's
`bazel-testlogs/<package>/<target>/test.outputs/lcov.info`. Go also preserves its
native block profile as `test.outputs/coverage.out`.

Python also preserves its branch-enabled coverage.py database as
`test.outputs/.coverage`. Its `py_coverage_test` rule requires `source_targets`
identifying the application libraries or binaries under test. Their transitive
workspace Python sources count toward coverage even when never imported;
external dependencies, test files, and tooling under `tools/` are excluded.
Reports are written before checking coverage thresholds or test success, so a
failing test still produces LCOV and raw data. A source-analysis error fails the
target explicitly and preserves the raw data for diagnosis.

All languages enforce **100% aggregate line coverage per target**, with the
minimum configured once in `tools/coverage/config.bzl`. Python additionally
measures branch coverage via `tools/coverage/python/.coveragerc`.
Reports are preserved even when the threshold fails. The shared line-coverage
minimum does not impose a branch/function threshold.
