# Python PostgreSQL validation

Native fixture validation on 2026-10-30, on branch
`feat/python-postgresql-flyway`. Host: macOS arm64, using Bazel's
`darwin-sandbox`. Runtime: Python 3.14, checksum-pinned PostgreSQL 17.10 native
binaries, Flyway OSS 11.20.3, SQLAlchemy 2.1.6, and Psycopg 3.3.6.

## Functional evidence

The native fixture and existing ORM/HTTP integration tests pass under Bazel
sandboxing without accessing Docker. The fixture's Python source passes the
repository's 100% combined line/branch coverage gate, lint, formatting, and type
checks.

- Static schema checks reject malformed SQL, equivalent duplicate versions,
  invalid filenames/configuration, empty files, and disabled placeholders.
- Python ORM tests cover exact bigint/numeric/UUID/bytea/JSONB/timestamp values,
  relationships, SQLSTATE constraint errors, three-table commit/rollback, and
  separation between migration and application permissions.
- An actual Uvicorn service process connects using the injected private file.
  Existing `/widgets` behavior and shared response-header requirements remain
  covered.
- A real failing migration prevents test execution, reaps PostgreSQL, removes
  database state and credentials, and retains structured Flyway diagnostics.
- Two simultaneous native fixtures accept conflicting primary keys independently.
- A real SIGTERM cancellation test verifies that both the coverage subprocess and
  postmaster have exited and their temporary directories are removed.
- Unit tests exercise initialization, spawn, readiness, migration, and test
  failures, bounded shutdown escalation, permissions, redaction, and development
  container recovery.
- Flyway results are checked using structured JSON as well as exit status;
  unsuccessful or missing success indicators cannot launch application tests.

The native process and declared inputs are subject to the selected Bazel sandbox.
Linux namespace isolation is stronger than macOS sandboxing. No manual hard kill
of an entire Bazel action is claimed validated here. Linux amd64 CI and native
macOS amd64/Linux arm64 execution still require separate qualification.

## Repeated local smoke measurements

These historical **container-backed** measurements were collected at `ebfe9d1`,
before replacing tests with native PostgreSQL or consolidating the database
routes into the existing app/server entrypoint. Current tests use that single
application and measure five intended source files; the six-file artifact count
below describes the original sample.

Executed through Bazel with artifacts/images already available:

```sh
bazelisk test //src/data/example/widgets:schema_test \
  //src/apis/examples/python:get_widgets_example_py_coverage_test \
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
