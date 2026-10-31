# Go PostgreSQL validation

The Go integration was rebuilt on main commit `3632660` (merged Python PR #54)
and validated on 2026-10-30 on macOS arm64. It reuses main's native sandboxed
PostgreSQL 17.10/Flyway fixture without changing the PostgreSQL lifecycle;
database tests do not require Docker.

Dependencies are pinned under `third_party/golang`: GORM 1.31.2, its PostgreSQL
driver 1.6.0, and pgx v5.6.0. Runtime code uses native GORM models, queries,
contexts, and transactions; Flyway owns migrations.

## Checks

- `bazelisk build //...` passed.
- `bazelisk test //...` passed: all 155 test targets, including Go and Python
  PostgreSQL integration tests. Unchanged results were cached.
- Go configuration, model, and service coverage targets each enforce the
  repository's existing 100% aggregate line threshold and emit portable
  `lcov.info` plus raw `coverage.out`.
- Configuration coverage is 38/38 lines, models/store 14/14, handler/startup
  36/36, and shared HTTP server 11/11. LCOV source records contain workspace-relative
  application paths. The binary's thin `main.go` entrypoint is exercised by process
  tests for successful startup, interrupt shutdown, and configuration failure.
- Model tests validate table/column bindings and relationship metadata against
  the shared schema contract. Connection tests validate configuration failures,
  TLS policy, bounded pooling, and real PostgreSQL authentication failures.
  The configuration test runs through the database coverage fixture and its
  native input target is manual, so it is counted once in wildcard test runs.
- Real GORM tests cover exact bigint/decimal/UUID/bytea/JSONB/timestamp values,
  nullable fields, parent/child loading, three-table commit/rollback, conditional
  version writes, SQLSTATE constraints, application permissions, and readiness
  and query failures.
- The Go app's existing `GET /widgets` returns `200` with persisted widget IDs,
  names, and owner names, including `[]` for an empty database. Missing database
  configuration returns `503`; query failures return `500`. Shared response
  headers apply. `/database/widgets` is not registered. The server entrypoint
  uses the connection file; no second app/server was introduced.
- Endpoint, header, and process tests seed a committed owner, widget, and outbox
  record before constructing the handler/server. The main endpoint test asserts
  the populated response's ID, Unicode name, and owner; empty-database behavior
  is checked in a separate test.
- Startup owns the connection pool and gives the handler a widget store.
  Shared transport construction and serving live in `src/apis/go/server`.
  The example's `run` returns errors and closes the pool before `main` handles
  process exit. Real connection-count checks verify cleanup after a listener
  failure and cancellation. Startup uses no mutable function globals.
  GORM queries live in the data package. Store tests check owner loading, stable
  ordering, more than 100 rows, request cancellation, and closed-pool errors.
  Listing has no implicit 100-row cap, matching the Python endpoint.
- A process test launches the actual Go server against the fixture, changes a row
  after startup, and verifies that HTTP reads the updated name and its owner.
  Startup and configuration tests call the real PostgreSQL opener; no database
  mocks or fabricated GORM handles are used.

The integration entrypoint is
`bazelisk test //src/apis/examples/go:get_widgets_example_go_coverage_test`.
The fixture runs inside Bazel's sandbox as described in the [usage guide](README.md).

Production deployment, native Linux qualification, full bidirectional/all-language
interoperability, and the proposal's complete contention/backfill/performance
benchmarks remain follow-up work. These checks establish the Go implementation
and its reuse of the shared fixture, not production adoption readiness.
