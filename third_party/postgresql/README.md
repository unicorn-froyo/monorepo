# PostgreSQL test binaries

Sandboxed tests use PostgreSQL 17.10 from
[Zonky's relocatable binary bundles](https://github.com/zonkyio/embedded-postgres-binaries).
The four platform archives are pinned by SHA-256 in
[`repositories.bzl`](../../tools/testing/postgresql/repositories.bzl) and fetched
by Bazel during dependency resolution, never by the test runner.

The selected distribution includes executables, bundled libraries, and SQL support
files as declared runfiles. macOS/Linux on arm64 and amd64 are supported. Standard
OS runtime libraries are still platform prerequisites; this is not a standalone
OS image. Linux distributions must be compatible with the upstream glibc build.
PostgreSQL refuses to run as root, so test executors must use an unprivileged user.

Upstream bundles include license files. PostgreSQL uses the PostgreSQL License;
the bundle project uses Apache-2.0. Docker-based local development retains its
separately pinned OCI image.
