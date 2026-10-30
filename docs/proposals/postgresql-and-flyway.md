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

Expose package-level targets for static schema linting, local development, and
integration tests. Deployment jobs consume the declared migration bundle and
shared Flyway runtime; no generic status/validation command rule is proposed.
Deployment migration execution is a runtime operation, not a cacheable build
action. Integration tests must disable result
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

## Proposed Bazel rules and providers

The following interfaces are implementation requirements, not existing targets.
Rule implementations emit launchers and manifests during analysis/build; they
never start containers or connect to databases in build actions. Runtime
orchestration uses a pinned, Bazel-built runner. There are no nested Bazel calls
inside migration launchers or test executables.

### Migration rules: `tools/migrations/flyway/index.bzl`

| Interface | Attributes and outputs | Behavior |
| --- | --- | --- |
| `flyway_migrations` | `srcs`: nonempty SQL labels; `schema`: SQL schema name; `history_table`: default `flyway_schema_history`; `script_configs`: optional labels for Flyway per-script configuration. Returns `FlywayMigrationsInfo` and declared runtime files. | Validates filenames, duplicate versions, and SQL/config pairing; produces a deterministic manifest with ordered paths, content digests, schema, and history-table identity. This packages migrations without executing them. |
| `flyway_schema_test` | `migrations`: requires `FlywayMigrationsInfo`; `lint_config`: optional declared configuration, defaulting to repository SQL policy. Returns a normal, cacheable Bazel test. | Statically checks migration names, duplicate versions, SQL/config pairing, supported script settings, and PostgreSQL SQL lint/parse diagnostics. No database, Docker, credentials, Flyway CLI, or JVM is required. |

`flyway_schema_test` names the repository's static test for Flyway migration
sources; it does not invoke Flyway's database-backed `validate` command. Use
pinned [SQLFluff with its PostgreSQL dialect](https://docs.sqlfluff.com/en/stable/reference/dialects/)
and a declared repository configuration for SQL linting. Reject parse errors and
do not silently skip large files or unsupported syntax. Keep Flyway placeholder
replacement disabled initially so linted SQL is the SQL executed. Any later
templating support must declare deterministic inputs for both lint and execution.
Pin linter dependencies through `third_party/pypi/` and host Python-specific
lint helpers under `tools/lint/python` if needed.

Linting checks source conventions and the linter's supported SQL grammar. It
cannot prove migration ordering against existing objects, deployed checksums,
permissions, lock behavior, or successful execution. Applying migrations and
checking database history remain responsibilities of the PostgreSQL-backed
coverage tests and deployment runtime. Do not start a container in this test.

Use a `flyway_toolchain` registration to supply the pinned CLI, JVM, PostgreSQL
module, and JDBC driver for the execution host. Document supported host
constraints; fail clearly on an unsupported host. The fixture/deployment runtime
selects its toolchain for the runnable target's platform, not an unrelated remote
build host. Static lint tests do not depend on this toolchain.
Script configs declare non-transactional exceptions; arbitrary runtime flags
cannot silently override migration locations or the safety defaults.

`FlywayMigrationsInfo` contains `sql_files`, `script_configs`, `manifest`,
`schema`, and `history_table`. Its runtime closure travels with every consuming
target. The manifest contains no credentials or environment-specific DB address.

### PostgreSQL rules: `tools/testing/postgresql/index.bzl`

| Interface | Attributes and outputs | Behavior |
| --- | --- | --- |
| `postgresql_fixture` | `migrations`: requires `FlywayMigrationsInfo`; `image`: pinned PostgreSQL OCI image target; `database`: default `testdb`; `extensions`: declared required extension names; `startup_timeout_seconds`: default 30; `migration_timeout_seconds`: default 60. Returns `PostgresqlFixtureInfo`. | Describes a fixture and its image/migration runfiles. Creates no running resources during build. Extensions must already be packaged in the selected image and created by declared migrations; readiness verifies their availability. |
| `postgresql_dev` | `fixture`; `persistent`: default false; `volume_name`: required when persistent; `startup_timeout_seconds`: default 30. A runnable target. | Starts and migrates a developer DB, writes a connection file with owner-only permissions, prints its path, and remains attached until interrupted. Cleans up disposable resources. An explicit `reset` subcommand is the only route to resetting a named development volume. |

Use a standard `test_suite` for the authoritative CI list of coverage targets
with PostgreSQL enabled. A separate PostgreSQL test rule or suite macro is not
needed.

`PostgresqlFixtureInfo` contains the migration provider, database name, required
extensions, timeouts, pinned image artifact/digest/platform metadata, and runtime
closure. Image targets provide a declared loadable OCI archive plus platform
metadata; the runner loads it using the configured container runtime. Do not run
an unpinned `docker pull` during a test. A container runtime toolchain supplies
the engine client and image loader; access to its daemon/socket is an explicit
execution requirement. Toolchain registration and OCI integration helpers live
under `tools/`, with native-platform image selection checked before startup.

### Optional fixture attribute on existing coverage rules

Add the same optional `postgres` label attribute to `py_coverage_test`,
`go_coverage_test`, `java_coverage_test`, `rb_coverage_test`, `rs_coverage_test`,
and `ts_coverage_test`. It requires `PostgresqlFixtureInfo` when supplied and
defaults to absent. Existing callers without the attribute retain their current
behavior and acquire no container tools, image downloads, or daemon requirement.

The coverage target remains the only public test target. When `postgres` is set,
its generated launcher runs the shared PostgreSQL setup runner around its normal
coverage command. The runner starts PostgreSQL, applies the declared Flyway
migrations, injects connection settings, invokes the language's coverage command,
and cleans up. Coverage instrumentation starts after DB setup; the fixture is
tested and covered separately under `tools/`.

Implement shared Starlark helpers and the lifecycle runner under
`tools/testing/postgresql`; extend the existing language rules under
`tools/coverage/{language}` to consume them. Shared helpers supply the optional
attribute, fixture manifest, runfiles, and execution requirements. Each language
supplies its existing coverage command and preserves its instrumentation contract.
Do not duplicate Docker/Flyway lifecycle logic six times or invoke Bazel inside
the runner. This is an internal launcher composition, not a second test target.

Pass a fixture target rather than a raw list of SQL files: the fixture carries
the same migration bundle used for deployment, including ordering, Flyway script
configs, schema/history identity, and image settings. Tests must not use a schema
dump or ORM-created tables instead of exercising production migrations.

When enabled, set the effective `local`, `external`, and `requires-docker`
execution requirements using Bazel-supported rule/provider or macro mechanisms.
Execute locally against the configured daemon and bypass test result caching.
Use `size = "large"` and an explicit Bazel `timeout` covering migrations, suite
execution, any service startup, and cleanup. Stage 0 verifies scheduling/cache
semantics with two consecutive invocations and verifies that non-DB tests retain
their existing cache behavior. Tags alone are not proof of these semantics.

### Runtime lifecycle and connection contract

The shared runner invoked by the coverage target owns this sequence:

1. Allocate unique resource names and labels using Bazel test/shard/run identity
   plus a random suffix. Register cleanup before creating any resources.
2. Start the PostgreSQL container with disposable storage and the pinned image.
   Poll an authenticated SQL query until ready or the startup deadline expires.
3. Run the declared Flyway bundle using a DDL role; create an application DML
   role for service and test connections. A migration failure prevents launching
   the coverage command or any service started by the suite.
4. Write a versioned JSON connection file under `TEST_TMPDIR`, with owner-only
   permissions. Set `POSTGRES_CONNECTION_FILE` to its absolute path for child
   processes. Its fields are `format_version`, `host`, `port`, `database`, `user`,
   `password`, and `sslmode`; adapters construct language-specific DSNs.
5. Provide service-test helpers for starting a host executable or service image
   using the fixture. The suite chooses which service to start and registers its
   cleanup with the helper. For container services, the helper mounts a second
   connection file containing the DB network alias and joins the test-owned
   network. Publish service ports on ephemeral loopback ports. Supply private
   runtime network metadata to the helper, not application DB configuration.
6. Invoke the existing coverage command directly. Tests that start services use
   bounded readiness polling before sending requests. Forward cancellation and
   preserve nonzero status; cleanup failure also fails an otherwise successful
   suite. Cleanup services before the database, using labels to discover service
   resources even after a suite crashes. Default cleanup deadline is 10 seconds.
7. Collect redacted diagnostics and coverage artifacts before deleting resources.
   Never copy connection files or credentials into `TEST_UNDECLARED_OUTPUTS_DIR`.
   Record cleanup failures and resource labels for the recovery command.

Service executables/images and their runtime files remain declared test data.
The service helpers do not build artifacts or supply a shared global fixture.
Runtime files are not Starlark providers: providers
describe build inputs, and the runner creates addresses and credentials at runtime.

### BUILD examples

An application database package declares the migration bundle and its static
test once, then reuses that bundle in its PostgreSQL fixture:

```starlark
load("//tools/migrations/flyway:index.bzl", "flyway_migrations", "flyway_schema_test")
load("//tools/testing/postgresql:index.bzl", "postgresql_dev", "postgresql_fixture")

flyway_migrations(
    name = "schema",
    srcs = glob(["migrations/*.sql"]),
    schema = "widgets",
    visibility = ["//src/apis/examples:__subpackages__"],
)

flyway_schema_test(name = "schema_test", migrations = ":schema")

postgresql_fixture(
    name = "postgres",
    migrations = ":schema",
    image = "//tools/testing/postgresql:postgres_image",
    visibility = ["//src/apis/examples:__subpackages__"],
)

postgresql_dev(name = "dev", fixture = ":postgres")
```

Each language retains its repository coverage rule and adds just the fixture
attribute. For example, a Python ORM integration suite declares:

```starlark
load("//tools/coverage/python:index.bzl", "py_coverage_test")
py_coverage_test(
    name = "database_integration_test",
    srcs = ["database_contract_test.py"],
    source_targets = [":application"],
    deps = [":application"],
    postgres = "//src/data/example/widgets:postgres",
    size = "large",
    timeout = "long",
)
```

The `application` and test sources are proposed integration targets. A suite can
connect directly to PostgreSQL or start a service through the shared test helper.
Service tests declare the server target in `data` and the helper in their
language dependencies, and read the same injected connection file. Any readiness
endpoint preserves the existing API example's `/widgets` behavior.

Use the same `postgres` attribute with `go_coverage_test`, `java_coverage_test`,
`rb_coverage_test`, `rs_coverage_test`, and `ts_coverage_test`; preserve their
language-specific arguments and thresholds. Implement the attribute uniformly
under `tools/coverage/{language}`. No plain lower-level test may replace a coverage
target to make DB integration easier.

The coverage rule merges fixture runfiles with its existing runtime closure,
preserves instrumentation metadata and Bazel coverage/test environment variables,
and saves reports even when the suite fails. Keep analysis-time instrumentation
of application sources intact rather than instrumenting only the launcher. Verify this with
a deliberately uncovered application branch/file and with a failing child suite
for every supported language. Preserve the existing coverage policy; the DB
fixture does not lower coverage thresholds.

Planned commands after implementation:

```text
bazelisk build //src/data/example/widgets:schema
bazelisk test //src/data/example/widgets:schema_test
bazelisk run //src/data/example/widgets:dev
bazelisk test //src/apis/examples/python:database_integration_test
bazelisk test //tools/testing/postgresql:integration_tests
```

`schema_test` runs in the ordinary unit-test lane without PostgreSQL. CI runs
the final integration suite target on workers with the declared container requirements, in
addition to `bazelisk build //...` and `bazelisk test //...`. Coverage targets with
`postgres` remain directly runnable and discoverable; the explicit suite contains
all six language integrations. Each test creates its own fixture; a
`test_suite` is a target grouping, not a shared database lifecycle.

### Rule implementation and acceptance

Stage 0 delivers providers, toolchains, `flyway_migrations`, `flyway_schema_test`,
`postgresql_fixture`, `postgresql_dev`, and the optional `postgres` attribute on
one existing coverage rule. Static test cases include accepted SQL, malformed SQL,
invalid filenames, equivalent duplicate version numbers, orphan script configs,
unsupported configuration, and attempted file skipping. Verify that the lint test
runs without a database/container runtime and that all source files are declared
inputs. Flyway-specific source checks share validation logic with bundle packaging.
Stage 1 tests analysis rejection of duplicate versions, wrong providers, missing
runfiles and unsupported platforms, plus runtime
readiness/migration failures and cleanup after interrupted children. Stage 2 adds
the same optional attribute to all six coverage rules and the explicit integration
suite. Existing unit-test BUILD declarations continue to work unchanged.

Add Bazel tests for the rules and runner under `tools/` using the same language
coverage rules as application code. The acceptance report must include a
successful BUILD example for each language, reports from failing coverage suites,
proof that two consecutive integration invocations actually execute, and service
connections from both host and container modes. The benchmark cases below are
executed through these targets, not a separate shell orchestration pipeline.

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
| Static schema lint | Check the 100-migration fixture with `flyway_schema_test`: median <= 5 s, maximum <= 10 s, with tool artifacts present and Bazel test caching disabled for measurement. Runs without network, database, or container runtime access; malformed SQL/config/name fixtures fail with file locations. |
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
