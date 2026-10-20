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
expose a Rack application. Go APIs use the standard `net/http` package. Rust APIs
use the shared HTTP routing and server library under `src/apis/rust`.

APIs are distributed as OCI-compatible images composed from Bazel-built layers
with `rules_oci`. Image targets are tagged `manual`, keeping image loading out of
normal `bazelisk build //...` operations.

Build the examples from the repository root:

```bash
bazelisk run //src/apis/examples/go:get_widgets_example_image
bazelisk run //src/apis/examples/python:get_widgets_example_image
bazelisk run //src/apis/examples/ruby:get_widgets_example_image
bazelisk run //src/apis/examples/rust:get_widgets_example_image
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
```

All examples serve `GET /widgets` on port 8080.

## Supported languages

Go, Python, Ruby, and Rust have hermetic Bazel toolchains. Use `go_*` rules from
`rules_go`, `py_*` rules from `rules_python`, `rb_*` rules from `rules_ruby`, and
`rust_*` rules from `rules_rust`. Python dependencies are locked in
`third_party/pypi/requirements.txt`; Ruby dependencies are locked in
`third_party/ruby/Gemfile.lock`.

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
