# Native PostgreSQL ORMs and shared Flyway migrations

- Status: **Direction approved; feasibility and implementation proposed**
- Date: 2026-10-29
- Audience: application, database, and build maintainers

## Decision and purpose

Use PostgreSQL with established, idiomatic ORMs in each application
language. Use Flyway as the shared schema migration runner, independently of
application runtimes. Provide containerized PostgreSQL for service integration
tests and local development through Bazel.

This replaces the proposed protobuf/DynamoDB repository generator in
[the original design](protobuf-dynamodb-data-access.md). Protobuf remains available for
API contracts or specific binary payloads, but is not the canonical database
schema and does not generate persistence APIs. Reviewed SQL migrations define
database structure. Applications retain their ORM's native transaction APIs.

Each service owns its database or a clearly bounded schema. Sharing a migration
standard does not require services to share tables. Cross-language fixtures prove
interoperability without granting production services access to each other's data.

The feasibility work must establish reproducible builds, a practical developer
workflow, safe migrations, and interoperability across all six existing languages.
The benchmark thresholds below are proposed acceptance budgets, not measured
results. The spike must publish measurements before production adoption.

## Application libraries

Adopt these ORMs as the defaults. These are established ecosystem choices,
not a claim that a single popularity ranking applies across every language.
Pin exact compatible versions during implementation in the existing ecosystem
dependency definitions and lockfiles under `third_party/`.

| Language | ORM and dependency | PostgreSQL integration |
| --- | --- | --- |
| Go | [GORM](https://gorm.io/docs/), `gorm.io/gorm` and `gorm.io/driver/postgres` | GORM models, associations, and transactions; PostgreSQL dialector backed by pgx. |
| Java | [Hibernate with Spring Data JPA](https://docs.spring.io/spring-data/jpa/reference/), Spring Boot Data JPA starter | Hibernate entities and JPA repositories; [pgJDBC](https://jdbc.postgresql.org/) driver and Spring-managed pooling/transactions. Pin versions compatible with the existing Spring stack. |
| Python | [SQLAlchemy ORM](https://docs.sqlalchemy.org/en/21/orm/), `sqlalchemy` | [Psycopg 3](https://www.psycopg.org/psycopg3/), `psycopg`, underneath; SQLAlchemy sessions, relationships, transactions, and pooling. |
| Ruby | [Active Record](https://guides.rubyonrails.org/active_record_basics.html), `activerecord` supplied by Rails | [ruby-pg](https://github.com/ged/ruby-pg), gem `pg`, underneath; Rails models, associations, transactions, and connection pooling. |
| Rust | [SeaORM](https://www.sea-ql.org/SeaORM/), crate `sea-orm` | PostgreSQL backend with Tokio-compatible runtime/TLS features; async entities, relationships, transactions, and pooling. |
| TypeScript | [Prisma ORM](https://docs.prisma.io/docs/orm/overview/introduction/what-is-prisma), `prisma` and `@prisma/client` | Generated typed client, relations, and transactions. Select and pin the PostgreSQL adapter required by the chosen release; use node-postgres where supported. |

The ORMs provide application persistence; Flyway alone owns schema migration
execution. Do not introduce a shared repository generator. Application APIs may
use ORM relationships and queries directly, with parameterized SQL escape hatches
where necessary. Bound pool sizes and document ownership of sessions/connections;
transactions must use the same ORM transaction context throughout an operation.

Disable competing schema mutation paths: Rails migrations and schema loading,
Hibernate automatic DDL updates, SQLAlchemy `create_all` and Alembic migrations,
GORM `AutoMigrate`, SeaORM migration/schema-sync facilities, and Prisma migration
or schema-push commands. Hibernate schema validation may remain enabled. Do not
let framework test setup silently replace Flyway with an ORM-created schema.

SQL migrations and ORM mappings are separate artifacts and must stay aligned.
Integration tests build a database using Flyway and exercise actual ORM models,
relationships, constraints, and transaction behavior. For
[Prisma's external migration workflow](https://docs.prisma.io/docs/orm/prisma-schema/introspection),
prove introspection and client generation under Bazel early, using the pinned
release's supported commands. If that release cannot support Flyway-owned SQL,
revisit the TypeScript ORM before expanding adoption.

Language APIs may differ. The shared requirements are correct SQL types, explicit
transaction boundaries, parameter binding, bounded pools/timeouts, TLS in deployed
environments, and useful PostgreSQL SQLSTATE diagnostics. Test `bigint` beyond
JavaScript's safe integer range, exact `numeric`, UUID, Unicode, `bytea`, JSONB,
NULL, and timestamp precision. Preserve exact values rather than requiring the
same host-language representation. Document any intentional precision limits.

## Shared migration contract

Use the [standalone Flyway CLI](https://documentation.red-gate.com/flyway/reference/usage/command-line)
with versioned PostgreSQL SQL files. Application deployments run a dedicated
migration job before releasing dependent application code. Application startup
does not independently run migrations.

Each logical database has one owning package, one ordered migration directory,
and one Flyway history table. Services sharing that database consume the same
history; they must not create competing histories for overlapping objects.
Independent databases can have independent histories and owners.

Use filenames such as `V20261029120000__create_widgets.sql` with UTC timestamps.
CI rejects duplicate versions and invalid names. Applied migrations are immutable;
make corrections with a new migration. Disable out-of-order execution and require
branches to reconcile their migration order before release. Use versioned
migrations initially; introduce repeatable migrations only with explicit semantics.

Run Flyway validation before migration and again afterward, configuring the
preflight to permit pending migrations while still rejecting altered or missing
applied migrations. [Validation checks migration checksums and history](https://documentation.red-gate.com/flyway/reference/commands/validate).
This does not establish that no one manually changed database objects; schema
drift detection requires a separate comparison and is not implied by validation.

Use transactional migrations by default. Separate operations such as
`CREATE INDEX CONCURRENTLY` into explicitly non-transactional migrations and test
their recovery procedure. [Flyway transaction handling](https://documentation.red-gate.com/flyway/flyway-concepts/migrations/migration-transaction-handling)
does not make every PostgreSQL operation atomic. Set lock and statement timeouts;
never wait indefinitely for a busy application table.

Use expand/backfill/contract changes: add compatible structure, deploy compatible
readers and writers, run resumable backfills, verify completion, then enforce
constraints or remove old structure in a later release. Keep large backfills out
of schema migration transactions. Prefer forward fixes; do not promise automatic
rollback of destructive schema changes. Application rollback must remain possible
during the compatibility window.

Use a migration role with DDL permissions and separate application roles with
only required DML permissions. Disable Flyway clean in deployed environments.
Do not automatically baseline unknown databases or repair checksum mismatches.
Recovery procedures must explain the database state and the intentional repair.

## Containerized PostgreSQL for tests and development

Provide one reusable fixture that starts a real PostgreSQL container, waits for
an authenticated SQL query to succeed, applies the package's Flyway migrations,
and supplies connection information to service processes. Test the production
major version and required extensions with pinned image digests. Select the exact
server version during the spike and record its support policy.

The fixture must support both host-run services and containerized services:

- Host processes receive a loopback address and an ephemeral published port.
- Service containers receive a network alias and PostgreSQL's internal port on
  an isolated test network. `localhost` inside a service container is not the DB.
- Tests receive structured host, port, database, user, password, and TLS settings;
  each language constructs its own DSN. Java receives a JDBC URL as appropriate.
- Concurrent suites receive distinct containers or isolated databases and roles.
  Database isolation is required when the service commits its own transactions;
  an outer test transaction is not sufficient.
- The fixture owns bounded startup, migration, and shutdown deadlines. It cleans
  up its containers, networks, and temporary storage on success and failure,
  preserves diagnostic logs in Bazel outputs, and labels resources for recovery
  after an uncatchable process termination.

Do not mount developer database directories or reuse an ambient local database.
Default fixtures use disposable storage. A separate local-development target may
use an explicitly named persistent volume, with an explicit reset operation.
Container runtime access is a declared integration-test requirement. A missing
runtime must produce a clear failure, not silently skip required CI tests.

Keep deterministic unit tests independent of Docker. Tag container integration
tests with their execution requirements and run them in a dedicated Linux CI
lane with a container runtime. The lane must explicitly execute those targets if
their scheduling tags exclude them from the general test invocation. Support
macOS local development through Docker Desktop, including Apple Silicon; validate
native Linux amd64 and arm64 where those architectures host services.

## Repository and Bazel integration

Proposed ownership layout (targets and directories are not implemented yet):

```text
src/data/<application>/<database>/
  BUILD.bazel
  migrations/
    V20261029120000__create_widgets.sql
tools/migrations/flyway/
  BUILD.bazel
  ... pinned CLI integration and migration rules
tools/testing/postgresql/
  BUILD.bazel
  ... container fixture, service harness, and integration-test rules
third_party/<ecosystem>/
  ... existing dependency definitions and lockfiles
```

All Starlark rules, macros, and helper files live under `tools/`. Put
language-specific helpers under `tools/{tool}/{language}` when needed. Dependency
resolution, orchestration, tests, and benchmark execution run through Bazelisk.
Pin Flyway, its PostgreSQL database module/JDBC driver, any JVM runtime, and
PostgreSQL images. Build artifacts must not depend on ambient Flyway, Java,
`psql`, or package-manager installations. Image acquisition can require network
access during setup; report cold acquisition separately from warm benchmarks.

Expose package-level targets for migration status, validation, application,
local development, and integration tests. Targets that mutate an external DB use
`bazel run`, not cacheable build actions. Integration tests must disable result
caching where external container state could invalidate results. Pass credentials
at runtime, keep them out of build outputs and logs, and never bake them into
artifacts. Versioned migration SQL is declared Bazel runtime data.

Use the existing language test, lint, formatting, typing, and coverage rules for
application and tool code equally. Any Node tooling is authored in TypeScript.
No source-generation step may connect to a developer's database. ORM generation
uses declared inputs and pinned tools; introspection uses only a disposable
database migrated from declared SQL. Expose introspection as an explicit Bazel
workflow that produces reviewable mapping inputs, then generate clients without
a live database during ordinary builds. CI must detect stale generated mappings
or schema inputs. Do not check in emitted runtime client code merely to avoid
hermetic generation.

## Feasibility plan and delivery

| Stage | Work and deliverable | Exit gate |
| --- | --- | --- |
| 0. Pin and package | Select supported PostgreSQL and Flyway releases, verify edition/license and required capabilities, package all runtime dependencies, and build a minimal schema plus container fixture. Prove Prisma's external migration, introspection, and hermetic generation workflow. | Reproducible macOS arm64 and Linux amd64 execution; record arm64 Linux support. No paid service or account required for the selected basic workflow. Prisma can consume Flyway-managed SQL without owning migrations. |
| 1. Prove migration safety | Implement history validation, concurrent-runner, interrupted-runner, transactional failure, and non-transactional recovery tests. Publish a recovery runbook. | All safety cases below pass. |
| 2. Prove ORM access | Add ORM/driver dependencies and an integration example in each of the six languages, using the same Flyway fixture schema. Exercise models, relationships, transactions, and mapping validation. | All six ORMs pass value, relationship, transaction, and schema compatibility contracts. No ORM changes the schema during startup or test setup. |
| 3. Measure deployment behavior | Run the benchmarks below and demonstrate expand/backfill/contract under service traffic. Publish raw reports and a decision record. | Correctness gates pass; performance budgets pass or receive an explicit evidence-based revision before adoption. |
| 4. Adopt one service | Assign DB ownership, wire the migration deployment job, document credentials and recovery, and deploy one bounded workload. | Staging exercise succeeds, owner signs off on reports, and monitoring and recovery are operational. |

Deliver each stage as reviewable PRs. Complete the fixture before language
examples so all languages use the same infrastructure. This proposal does not
select the production hosting service, provisioning system, or pooling proxy.
Resolve those before the pilot; test the actual hosting configuration in staging.

## Benchmarks and correctness gates

Run on an otherwise idle Linux amd64 worker with at least four vCPUs, 8 GiB RAM,
and local SSD. Record actual resources, image digests, source commit, runtime and
library versions, PostgreSQL settings, and commands. Give PostgreSQL two CPUs
and 2 GiB RAM for the reference workload. Re-run functional tests on macOS arm64
and deployed Linux architectures; do not compare their timings directly.

Use a deterministic dataset of one million widgets with UUID IDs, owner IDs,
`bigint` versions, timestamps, exact numeric amounts, and a 1 KiB payload. A
separate fixture contains 100 small versioned DDL migrations. Run timing cases
five times, reporting every run plus median and maximum. Service traffic tests
use 30 seconds of warmup and five minutes of measurement at a fixed 100
operations/second, 20 clients, and an 80/20 point-read/update mix. Record offered
and achieved rate, p50/p95/p99 latency, errors, lock waits, CPU, and memory.

| Case | Concrete acceptance criterion |
| --- | --- |
| Warm fixture startup | From Bazel-launched harness start to successful migrated SQL connection: median <= 15 s, maximum <= 30 s, with images and build artifacts present. Report image download/build separately. |
| Empty DB replay | Apply the 100-migration DDL fixture: median <= 30 s, maximum <= 60 s, excluding container startup. Compare resulting normalized schema with the expected schema. |
| No-op deployment | Validate/migrate/validate an up-to-date 100-migration database: median <= 5 s, maximum <= 10 s, including CLI startup. No schema or application-data changes. |
| Concurrent runners | Start two migration runners together, repeated 100 times. Each migration's non-idempotent sentinel effect occurs once; one successful history entry per version; no overlapping DDL execution. Both runners finish or return a documented bounded lock-timeout result. |
| Transaction failure | Fail a migration after its first DDL and data change, repeated 100 times. Neither effect commits, later migrations do not run, and retry after correcting the unapplied fixture succeeds. |
| History integrity | Editing or removing an applied fixture migration and introducing duplicate versions must fail before new DDL executes. Reconciled branch migrations apply in the intended order. |
| Interruption and recovery | Terminate runners before commit, after commit, and during a concurrent-index migration. Twenty repetitions per case; recovered schema/history agree, no duplicate effects, and any leftover invalid index is diagnosed and recovered using the runbook. |
| Fixture isolation | Run 12 service suites concurrently for 20 rounds. No cross-suite data visibility, port collisions, or resource leaks after normal/failure cleanup. Simulated hard-kill resources are discoverable by labels and removed by the recovery target. |
| Language interoperability | All six clients read values written by every other client: 36 writer/reader pairs. Exact values survive, including bigint and numeric edge cases; intentional timestamp limits are checked. |
| ORM mappings and relationships | Each ORM loads and updates an order with multiple line items and an owner through mapped relationships. Foreign-key, unique, and NULL constraints produce expected errors. A deliberately incompatible column change fails mapping validation or an integration query in all six suites. Schema remains unchanged after ORM startup and test setup. |
| Transaction contract | Each language commits and rolls back a three-table order/inventory/outbox transaction. In 1,000 competing attempts against inventory 100, exactly 100 reservations succeed and outbox/order counts match. Retry policy handles serialization failures without duplicating business effects. |
| Rolling schema change | Old and new service versions operate during additive DDL, resumable backfill, and concurrent index creation. Zero schema-related errors or invariant violations; achieved throughput >= 99% of offered load and p95 latency <= 1.2x the no-migration baseline. |
| Bounded blocking | Hold a conflicting lock; migration fails within a configured 2 s lock timeout plus <= 3 s CLI/reporting allowance. No later migration executes; application traffic recovers after lock release. |
| Backfill restart | Backfill all one million rows in batches of at most 1,000, interrupt five times, then resume. Finish within 10 minutes total active runtime while meeting the rolling-change traffic budget; no missed rows or overwritten newer application values. |

Freeze SQL, indexes, pool sizes, and retry policies for comparisons. Run the traffic
case separately per client rather than treating language-to-language latency as a
parity requirement. Define the no-migration baseline on the identical populated
database and service build. Use SQL catalog assertions and business invariants
in addition to process exit codes. ORM/driver performance differences are reported;
shared correctness and operational budgets are the adoption requirements.

## Adoption decision and remaining work

Publish a results document linked from this proposal with pass/fail per gate,
raw benchmark artifacts, known limitations, recovery transcripts, and the exact
Bazel commands. There are no results yet. Do not describe Flyway integration,
container fixtures, or the ORM integrations as implemented until those stages land.

Adopt after the safety and all-language gates pass and the pilot demonstrates
the expected migration/deployment workflow. If an ORM or driver fails integration, resolve
or explicitly revise that language's choice. If Flyway cannot meet the required
workflow in the selected edition, reassess the tool rather than build a custom
migration engine. Performance-budget changes require published evidence and a
proposal revision; correctness requirements are not traded for speed.

Every implementation PR runs `bazelisk build //...` and `bazelisk test //...`
plus the explicit container integration lane and relevant benchmarks. API examples
retain the [cross-platform API standards](../../src/apis/STANDARDS.md).
