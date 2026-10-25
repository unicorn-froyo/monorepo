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
includes branch coverage in its existing coverage.py threshold via
`tools/coverage/python/.coveragerc`.
Reports are preserved even when the threshold fails. The shared line-coverage
minimum does not impose a branch/function threshold.

| Language | Coverage gate | Branch behavior |
| --- | --- | --- |
| Go | Aggregate lines converted from native block profiles | No separate branch gate |
| Python | coverage.py aggregate statements and branches, requiring both to be fully covered at 100% | Branch measurement and enforcement enabled |
| Ruby | Aggregate lines | Branch measurement disabled |
| Rust | Aggregate LLVM lines | No separate branch gate |
| TypeScript | Aggregate V8 lines mapped to sources | Branches collected; threshold explicitly zero |

`rb_coverage_test` accepts one or more `srcs` test scripts, loads them in order
in one Ruby process, and accepts runtime files through `data`.
`ts_coverage_test` accepts either the existing `entry_point` string or a nonempty
`entry_points` list; Node runs each suite in a separate process and c8 combines
their coverage. Both forms preserve declared runtime `data`.
