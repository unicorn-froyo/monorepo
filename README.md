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

## Supported languages

Go, Python, Ruby, Rust, and TypeScript have hermetic Bazel toolchains. Use
`go_*` rules from `rules_go`, `py_*` rules from `rules_python`, `rb_*` rules from
`rules_ruby`, `rust_*` rules from `rules_rust`, and `ts_project` from
`aspect_rules_ts`. Go dependencies are locked in `go.sum`, Python dependencies
in `third_party/pypi/requirements.txt`, Ruby dependencies in
`third_party/ruby/Gemfile.lock`, Rust dependencies under `third_party/rust`, and
TypeScript dependencies in `pnpm-lock.yaml`.

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
