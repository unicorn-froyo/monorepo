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

Model persistence, relationships, transactions, constraints, and role permissions
are tested alongside the mappings in
[`example/widgets/python/models_test.py`](example/widgets/python/models_test.py).
The API's `database_test.py` covers HTTP behavior, request-session cleanup, and
server startup. Both suites use the migrated PostgreSQL fixture and are included
in the integration suite above.

The optional attribute starts PostgreSQL 17.10 as a foreground child process
inside the Bazel test sandbox. Checksum-pinned Zonky binary distributions, including
their libraries and SQL support files, are declared Bazel inputs for macOS/Linux
arm64 and amd64. No host PostgreSQL installation or Docker daemon is required.
Flyway OSS 11.20.3 uses Bazel's Java 21 runtime to migrate and validate the schema
before the existing coverage command starts.

All database state and private credentials live under `TEST_TMPDIR`. Fixtures use
separate migration and application roles, SCRAM authentication, random passwords,
and loopback ephemeral ports. The application role can perform DML but cannot run
DDL or access Flyway's history table. `POSTGRES_CONNECTION_FILE` names a private
JSON file inherited by tests and subprocess services. Python APIs using
`AbstractApiBase` load this file automatically during application startup. Other services can use `engine_from_file()` from
`src.data.python.postgresql.config`.

`startup_timeout_seconds` defaults to 30 seconds for initialization and separately
for SQL readiness; `migration_timeout_seconds` defaults to 60 seconds per Flyway
command. Readiness authenticates and executes `SELECT 1`. The test target's Bazel
timeout bounds the entire invocation. PostgreSQL must run as an unprivileged user.

The runner keeps PostgreSQL in the test's process group, stops and reaps it on
completion or handled cancellation, and removes database files and credentials.
Bazel's configured sandbox/process supervision handles action termination; there
are no daemon-owned containers to recover. These tests retain normal sandboxing
and test caching. Linux namespace isolation is stronger than macOS sandboxing;
this does not add network isolation beyond what the selected Bazel sandbox offers.

Each test writes `lcov.info`, raw coverage, redacted initialization,
Flyway/PostgreSQL logs, and `lifecycle.log` to Bazel's undeclared test outputs.
Lifecycle timings include initialization, SQL readiness, migration, and grants;
cleanup duration, postmaster PID, port, and exit code are recorded separately.
Credentials and database files are never copied into test outputs.

## Local development

```sh
bazelisk run //src/data/example/widgets:dev
```

This development target retains the digest-pinned PostgreSQL container and uses
the pinned Python Docker SDK. Set `DOCKER_HOST` when the daemon is not available
at `/var/run/docker.sock` (for example, `unix://$HOME/.colima/default/docker.sock`).
Image imports allow 120 seconds; other Docker API calls allow 10 seconds.

The target prints a private connection-file path. Set `POSTGRES_CONNECTION_FILE`
to that path in a second shell, then run:

```sh
bazelisk run //src/apis/examples/python:server
```

The service listens on port 8080. `GET /widgets` returns `200` with stored
widgets ordered by ID, including each widget's ID, name, and owner name; an empty
database returns `[]`. `/readyz` checks database connectivity when configured.
The shared API base uses the connection file when configured. Without database
configuration, `/widgets` returns 503.

The shared `AbstractApiBase` creates a bounded SQLAlchemy engine from
`POSTGRES_CONNECTION_FILE` during FastAPI startup and disposes it on shutdown.
It registers `/readyz` and exposes `database_session` as a FastAPI dependency.
Routes declare `session: Session = Depends(self.database_session)` and keep
application queries in the route. Each request closes its session on success or
failure, rolling back unfinished transactions; writes must explicitly use
`session.begin()` or `session.commit()`. Tests may inject an engine instead;
its caller owns disposal. The API never changes the schema. The server entrypoint
only starts Uvicorn.

Stop the service before interrupting the development DB target. The database and
its data are disposable; persistent-volume/reset workflows are not implemented in
this first slice.

For container-based development only, `POSTGRES_CONTAINER_CONNECTION_FILE` and
`POSTGRES_TEST_NETWORK` allow a service container to connect. After a hard kill,
recover the development fixture using its printed label:

```sh
bazelisk run //tools/testing/python:postgresql_runner -- \
  --cleanup-run bazel-postgres-<32-character-uuid>
```

Recovery removes only containers/networks with that exact fixture label.

## Scope and remaining adoption work

This implementation supplies shared migration packaging, static checks, Python
coverage fixtures, disposable development databases, recovery, connection
configuration, and a real ORM/HTTP example. Repository-wide `bazelisk test //...`
includes sandboxed database integration tests without requiring Docker. The
integration suite above can also be run directly.

The [proposal](../../docs/proposals/postgresql-and-flyway.md) still governs later
work: other language integrations, production migration-job packaging and hosting,
persistent development storage, containerized-service helpers, registered runtime
toolchains, the complete stress/rollout/backfill benchmark suite, and staging
recovery exercises. Flyway source validation is not deployment drift detection.
Do not infer production readiness from the example integration tests.
