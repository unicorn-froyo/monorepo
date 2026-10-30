# PostgreSQL development and testing

Python uses SQLAlchemy ORM with Psycopg 3. Flyway owns database migrations;
application startup never creates tables. The example schema lives in
[`example/widgets/migrations`](example/widgets/migrations), with mappings in
[`example/widgets/python/models.py`](example/widgets/python/models.py).

## Static schema checks

```sh
bazelisk test //src/data/example/widgets:schema_test
```

`flyway_schema_test` checks Flyway versioned filenames, equivalent duplicate
versions, script configuration, and PostgreSQL SQL lint/parse errors. It runs
offline, without PostgreSQL, Docker, Java, or Flyway. SQLFluff is pinned; inline
`noqa` directives and large-file skipping cannot bypass the check. Only
`executeInTransaction=true/false` script configs are supported; Flyway
placeholders are disabled. Include every migration with `glob(["migrations/*.sql"])`.

This is source validation. Applying migrations against real PostgreSQL is part
of integration testing. Never use `metadata.create_all()` as a test shortcut.

## Tests with a database

```starlark
py_coverage_test(
    name = "database_integration_test",
    srcs = ["database_test.py"],
    source_targets = [":application"],
    deps = [":application"],
    postgres = "//src/data/example/widgets:postgres",
    size = "large",
    timeout = "long",
)
```

```sh
bazelisk test //tools/testing/postgresql:integration_tests
```

The optional attribute starts an isolated PostgreSQL 17 container from a
digest-pinned OCI archive, applies migrations with Flyway OSS 11.20.3 using
Bazel's Java 21 runtime, and runs the existing coverage command. A private JSON
file named by `POSTGRES_CONNECTION_FILE` supplies connection settings. Python
services can call `engine_from_file()` from `src.data.python.postgresql.config`;
it constructs a bounded SQLAlchemy pool without altering the schema.

Fixtures use separate migration and application roles, loopback ephemeral ports,
isolated networks, random credentials, and disposable storage. The application
role can perform DML but cannot run DDL or access Flyway's history table. Tests
without `postgres` retain normal execution and caching, with no Docker/image
dependency. Database tests use local/external execution requirements and bypass
test result caching. A missing daemon fails the integration tests.

The Docker client is the pinned Python SDK, not a host `docker` executable.
The daemon must be accessible through `DOCKER_HOST` or `/var/run/docker.sock`.
For Colima, for example, set `DOCKER_HOST=unix://$HOME/.colima/default/docker.sock`
in your shell before running Bazel. `.bazelrc` forwards this variable to tests.
Docker Desktop users should likewise set the socket endpoint when it differs
from the default; the SDK does not read Docker CLI contexts. Native macOS/Linux
arm64 and amd64 select the corresponding pinned Linux container image.

Each test writes `lcov.info`, raw coverage, redacted Flyway/PostgreSQL logs, and
`lifecycle.log` to Bazel's undeclared test outputs. Lifecycle timings are seconds
from fixture start for image loading, SQL readiness, and completed migration;
cleanup duration is reported separately. Credentials are never copied into
test outputs. The fixture removes its resources after tests, setup failures,
and normal cancellation. After a hard kill, use its exact recovery label:

```sh
bazelisk run //tools/testing/python:postgresql_runner -- \
  --cleanup-run bazel-postgres-<32-character-uuid>
```

Recovery removes only containers/networks with that exact fixture label. It does
not remove persistent developer data or unrelated Docker resources.

The host connection file is also inherited by subprocess services. A separate
`POSTGRES_CONTAINER_CONNECTION_FILE` contains the DB network alias for a service
container; mount that file read-only and join `POSTGRES_TEST_NETWORK`. Tag owned
service containers with `com.unicorn-froyo.postgresql-test=POSTGRES_TEST_LABEL`
so fixture cleanup can remove them. The Python example includes an actual host
service process test; containerized-service orchestration helpers remain future
work.

## Local development

```sh
bazelisk run //src/data/example/widgets:dev
```

The target prints a private connection-file path. Set `POSTGRES_CONNECTION_FILE`
to that path in a second shell, then run:

```sh
bazelisk run //src/apis/examples/python:server
```

The existing service listens on port 8080, retains `GET /widgets` returning
`202 []`, and exposes `/database/widgets` and `/readyz`. Its existing entrypoint
uses the connection file when configured; there is no separate database app or
server. Without database configuration, the database query endpoint returns 503
and ordinary `/widgets` behavior remains available. Stop the service before
interrupting the development DB target. The database and its data are disposable;
persistent-volume/reset workflows are not implemented in this first slice.

## Scope and remaining adoption work

This implementation supplies shared migration packaging, static checks, Python
coverage fixtures, disposable development databases, recovery, connection
configuration, and a real ORM/HTTP example. Repository-wide `bazelisk test //...`
includes the container integration tests. The integration suite above can also be
run directly; use `--test_tag_filters=-requires-docker` for a unit-only invocation
on machines without a container daemon.

The [proposal](../../docs/proposals/postgresql-and-flyway.md) still governs later
work: other language integrations, production migration-job packaging and hosting,
persistent development storage, containerized-service helpers, registered runtime
toolchains, the complete stress/rollout/backfill benchmark suite, and staging
recovery exercises. Flyway source validation is not deployment drift detection.
Do not infer production readiness from the example integration tests.
