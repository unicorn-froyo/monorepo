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
expose a Rack application.

APIs are distributed as OCI-compatible images built with `rules_oci`. Each
deployable API owns its Dockerfile. Image targets are tagged `manual`, keeping
container-daemon access out of normal `bazelisk build //...` operations.

Build the examples from the repository root:

```bash
bazelisk run //src/apis/examples/python:get_widgets_example_image
bazelisk run //src/apis/examples/ruby:get_widgets_example_image
```

Run the resulting containers:

```bash
docker run --rm -p 8080:8080 get-widgets-python:latest
# or
docker run --rm -p 8080:8080 get-widgets-ruby:latest
```

Both examples serve `GET /widgets` on port 8080.

## Supported languages

Python and Ruby have hermetic Bazel toolchains. Use `py_*` rules from
`rules_python` or `rb_library`, `rb_binary`, and `rb_test` from `rules_ruby`.
Python dependencies are locked in `third_party/pypi/requirements.txt`; Ruby
dependencies are locked in `third_party/ruby/Gemfile.lock`.

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
