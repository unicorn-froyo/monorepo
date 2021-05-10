# monorepo

## Description

This template repository implements a polyglot monorepository structure using [Bazel](https://www.bazel.build/) as the build tool.

## Principles

1. Builds are hermetic.
2. Commits are atomic.

## How-to

### Install Bazel

It is recommended you install [Bazelisk](https://github.com/bazelbuild/bazelisk) to manage Bazel executions. It's primary benefit is to manage running the correct version of bazel for your workspace.

On Mac install via homebrew:

```bash
$ brew install bazelisk
```

You may also install manually via the [Bazelisk Github Releases](https://github.com/bazelbuild/bazelisk/releases).

### Build

Once installed build is as simple as running the below command.

```bash
# if not using bazelisk replace w/ bazel
bazelisk build //...
```

### Test

Testing your projects is as simple as running the below command.

```bash
# if not using bazelisk replace w/ bazel
bazelisk test //...
```
