# Python PostgreSQL validation

Local validation on 2026-10-30, on branch `feat/python-postgresql-flyway` based
on `5d0ff0f`. Host: macOS arm64 with Colima and Docker Engine 29.2.1. Runtime:
Python 3.14, PostgreSQL 17.10 from the pinned PostgreSQL image, Flyway OSS
11.20.3, SQLAlchemy 2.1.6, and Psycopg 3.3.6.

## Functional evidence

`bazelisk build //...` and `bazelisk test //...` pass: 142 test targets, with
the database suites executing against the local daemon. The final test invocation
reused unchanged test results and executed the changed Python checks and external
database tests. New Python source remains subject to the existing 100% combined
line/branch coverage threshold.

- Static schema checks reject malformed SQL, equivalent duplicate versions,
  invalid filenames/configuration, empty files, and disabled placeholders.
  Inline suppression and large-file skipping do not bypass SQL validation.
- Python ORM tests cover exact bigint/numeric/UUID/bytea/JSONB/timestamp values,
  relationships, SQLSTATE constraint errors, three-table commit/rollback, and
  separation between migration and application permissions.
- An actual Uvicorn service process connects using the injected private file.
  Existing `/widgets` behavior and shared response-header requirements remain
  covered.
- Real failing migrations prevent test execution and leave no fixture containers
  or networks. Two simultaneously running fixtures accept conflicting primary
  keys independently, proving database/port isolation.
- Tests for startup failures, test failures, cancellation, log failures, secret
  file permissions, explicit recovery, and development lifecycle pass under the
  repository's unchanged 100% Python line/branch coverage gate.
- The development target was started with `bazel run`, reached readiness, and
  shut down successfully on Ctrl-C. No labeled fixture containers remained.
- Flyway results are checked using structured JSON as well as exit status;
  unsuccessful or missing success indicators cannot launch application tests.

## Repeated local smoke measurements

These measurements were collected at `ebfe9d1`, before consolidating the database
routes into the existing app/server entrypoint. Current tests use that single
application and measure five intended source files; the six-file artifact count
below describes the original sample.

Executed through Bazel with artifacts/images already available:

```sh
bazelisk test //src/data/example/widgets:schema_test \
  //src/apis/examples/python:database_integration_test \
  --runs_per_test=5 --nocache_test_results
```

`DOCKER_HOST` was configured for the local Colima socket. Bazel ran repetitions
concurrently. These are measurements of the **single-migration example**, not
the proposal's 100-migration/one-million-row reference benchmarks or Linux
production qualification.

| Measurement | Result |
| --- | --- |
| Static schema test, five runs | All pass; approximately 1.2 s per run |
| Complete ORM/HTTP suite, five runs | All pass; 5.4–8.0 s, mean 6.5 s |
| Fixture setup through migration and grants | 2.964, 6.009, 4.489, 4.743, 3.356 s; median 4.489 s |
| Fixture cleanup | 0.130–0.268 s |
| Coverage artifacts | All five runs contain LCOV with six intended workspace-relative source paths |

Fixture timings start on entry to the lifecycle function. They include loading
the pinned archive into Docker, SQL readiness, migration, validation, and grants;
they exclude Bazel build/download time, Python imports, and Docker client
initialization. Full-suite times include setup, tests, and cleanup. The raw
`lifecycle.log`, `.coverage`, and `lcov.info` files are in the corresponding
`bazel-testlogs/.../run_*_of_5/test.outputs` directories.

## Remaining qualification

Production deployment jobs, persistent development volumes, containerized service
helpers, non-Python integrations, and the proposal's full contention, rollout,
backfill, and large-dataset benchmarks are not implemented or claimed validated
by this Python change. Native Linux amd64 CI and additional deployment-platform
qualification remain required before production adoption.
