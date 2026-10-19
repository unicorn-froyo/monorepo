# Protobuf DynamoDB Data Access Design

Status: Proposed

## Summary

The data layer will use protocol buffer messages as its canonical application data
contracts and generate Python repositories for DynamoDB access. Protocol buffers,
the Python runtime library, code generation, and domain data schemas will all live
under `src/data`.

Each DynamoDB item will use a hybrid representation:

- Keys, secondary-index keys, version, TTL, and explicitly projected fields are
  stored as native DynamoDB attributes.
- The complete protocol buffer message is stored as a binary payload.
- Generated repositories own conversion between the two representations and
  prevent callers from updating them independently.

This is a repository generator, not an active-record ORM. Generated protobuf
classes remain plain messages and are never subclassed to add persistence methods.

## Goals

- Make `.proto` files the source of truth for persisted application data.
- Generate typed Python APIs for declared DynamoDB access patterns.
- Keep physical keys and indexes visible and intentional in schema review.
- Preserve protobuf compatibility and cross-language payload readability.
- Support optimistic concurrency, pagination, conditional writes, and TTL.
- Keep builds and code generation reproducible under Bazel and Bazelisk.
- Test repository behavior against a real DynamoDB-compatible implementation.

## Non-goals

- Relational features such as joins, foreign keys, lazy loading, or a unit of work.
- An arbitrary expression language or queries inferred from message fields.
- Hiding DynamoDB partition and sort key design.
- Provisioning tables, indexes, alarms, backups, or IAM policies.
- Automatically backfilling data after key or index changes.
- Supporting scans in normal generated repositories.
- Partial updates of arbitrary protobuf fields in v1.
- An asynchronous Python API in v1.

## Repository Layout

All data access libraries and protocol buffers live under `src/data`:

```text
src/data/
  DESIGN.md
  proto/
    dynamodb/
      options.proto
  python/
    dynamodb/
      BUILD.bazel
      client.py
      codec.py
      config.py
      errors.py
      pagination.py
      repository.py
      testing.py
    dynamodb_codegen/
      BUILD.bazel
      defs.bzl
      protoc_gen_dynamodb.py
      generator/
  go/
    dynamodb/
      BUILD.bazel
      client.go
      codec.go
      errors.go
      pagination.go
      repository.go
    dynamodb_codegen/
      BUILD.bazel
      defs.bzl
      main.go
      generator/
  <application>/
    <library>/
      BUILD.bazel
      <entity>.proto
```

The directory boundaries have these responsibilities:

| Path | Responsibility |
| --- | --- |
| `src/data/proto` | Shared protobuf annotations and data-layer contracts |
| `src/data/python/dynamodb` | Python runtime used by generated repositories |
| `src/data/python/dynamodb_codegen` | Python `protoc` plugin and generator implementation |
| `src/data/go/dynamodb` | Go runtime used by generated repositories |
| `src/data/go/dynamodb_codegen` | Go `protoc` plugin and generator implementation |
| `src/data/<application>/<library>` | Application-owned protobuf data libraries |

Generated Python and Go files belong in Bazel's output tree and will not be checked
into source control.

Persisted protobufs are organized as Bazel libraries within their owning
application. For example, a `widget` data library belonging to the `example`
application lives at:

```text
src/data/example/widget/
  BUILD.bazel
  widget.proto
```

The application and library directories are ownership boundaries, not protobuf
type categories. A library may contain multiple closely related messages and owns
its Bazel dependencies and visibility. Application messages must not be collected
in the shared `src/data/proto` directory; that directory is reserved for
cross-application data-layer contracts such as DynamoDB annotations.

All handwritten Python libraries in this design live beneath `src/data/python`.
They are split into Bazel packages by responsibility rather than placed directly
in an application protobuf package. The Python generator emits only Python and is
owned by the Python directory. Go uses the equivalent `src/data/go/dynamodb` and
`src/data/go/dynamodb_codegen` layout. Each language reuses the shared options
protobuf and storage contract but owns its language-specific runtime, generator,
and Bazel rules.

API transport schemas may continue to live under `src/apis`. A persisted message
must live under `src/data`; transport and persistence messages should be distinct
when they have different compatibility or security requirements.

## Schema Annotations

The data layer will define custom message options in
`src/data/proto/dynamodb/options.proto`. A message annotation declares the logical
table, physical key templates, indexes, projections, concurrency field, and TTL
field.

An illustrative annotation schema is:

```proto
syntax = "proto3";

package unicorn.data.dynamodb;

import "google/protobuf/descriptor.proto";

message KeyTemplate {
  string partition_attribute = 1;
  string partition_template = 2;
  string sort_attribute = 3;
  string sort_template = 4;
}

message SecondaryIndex {
  string name = 1;
  KeyTemplate key = 2;
  string query_name = 3;
}

message EntityOptions {
  string entity_name = 1;
  string table_id = 2;
  KeyTemplate primary_key = 3;
  repeated SecondaryIndex indexes = 4;
  repeated string projected_fields = 5;
  string version_field = 6;
  string ttl_field = 7;
  uint32 storage_version = 8;
}

extend google.protobuf.MessageOptions {
  EntityOptions entity = 51000;
}
```

The final extension number must be reserved for this repository and centrally
owned. The option shape may evolve during the implementation spike, but the
semantics in this document are required.

Example entity:

```proto
syntax = "proto3";

package unicorn.data.example.widget;

import "src/data/proto/dynamodb/options.proto";

message Widget {
  option (unicorn.data.dynamodb.entity) = {
    entity_name: "widget"
    table_id: "application"
    primary_key: {
      partition_attribute: "PK"
      partition_template: "ACCOUNT#{account_id}"
      sort_attribute: "SK"
      sort_template: "WIDGET#{widget_id}"
    }
    indexes: {
      name: "GSI1"
      query_name: "by_owner"
      key: {
        partition_attribute: "GSI1PK"
        partition_template: "OWNER#{owner_id}"
        sort_attribute: "GSI1SK"
        sort_template: "WIDGET#{widget_id}"
      }
    }
    projected_fields: "owner_id"
    version_field: "version"
    ttl_field: "expires_at_epoch_seconds"
    storage_version: 1
  };

  string account_id = 1;
  string widget_id = 2;
  optional string owner_id = 3;
  string display_name = 4;
  int64 version = 5;
  optional int64 expires_at_epoch_seconds = 6;
}
```

The generator will reject annotations that are incomplete or ambiguous. In
particular:

- Every template placeholder must name a scalar field on the message.
- Primary key placeholders must have explicit field presence or a type whose
  default value is a valid, intentional key value.
- String and byte placeholders used in a key must be non-empty.
- Index key fields that may be absent produce a sparse index by omitting all of
  that index's key attributes.
- A partially populated index key is invalid.
- Version fields must be integer scalars.
- TTL fields must be integer epoch seconds.
- Projected fields must use a supported native DynamoDB encoding.
- Query method names must be unique Python identifiers.
- Physical attribute names reserved by the runtime cannot be projected.

Environment-specific physical table names do not belong in protobuf schemas.
`table_id` is a stable logical identifier resolved by runtime configuration.

Key templates always render a DynamoDB string. Literal template text is copied as
written. Placeholder values use a canonical, language-independent representation:

| Placeholder type | Key representation |
| --- | --- |
| `string` | UTF-8 with every byte outside RFC 3986 unreserved characters percent-encoded |
| `bytes` | Unpadded base64url |
| Signed and unsigned integers | Base-10 ASCII with no leading zeroes |
| Enum | Base-10 numeric value |

Boolean, floating-point, timestamp, message, repeated, map, and oneof values cannot
appear in v1 key templates. Percent signs and delimiters such as `#` in string
values are encoded, so a placeholder cannot collide with template literals. Each
language implementation must pass shared key-rendering fixtures before release.

## DynamoDB Item Format

A stored item has this general shape:

| Attribute | DynamoDB type | Purpose |
| --- | --- | --- |
| `PK`, `SK` | `S` | Primary key attributes rendered from templates |
| `GSI<n>PK`, `GSI<n>SK` | `S` | Secondary-index keys rendered from templates |
| `_entity` | `S` | Stable entity name for diagnostics and validation |
| `_message_type` | `S` | Fully qualified protobuf message name |
| `_storage_version` | `N` | Version of the storage mapping |
| `_version` | `N` | Optimistic concurrency value, when configured |
| `_payload` | `B` | Serialized protobuf message |
| TTL attribute | `N` | Epoch seconds, when configured and present |
| Projected attributes | native | Fields needed outside the binary payload |

Physical key attribute names are schema-controlled and may differ from the names
shown above. Runtime metadata names beginning with `_` are reserved.

`_payload` is produced with protobuf binary serialization. Deterministic
serialization may be enabled for stable tests, but callers must not treat it as a
canonical byte representation or derive identity from its hash.

The repository builds the complete item for every write. Callers cannot supply raw
key, projection, version, or payload attributes. This guarantees that duplicated
projected fields and the payload are written in one DynamoDB operation.

On reads, the codec validates `_entity`, `_message_type`, and `_storage_version`
before decoding. A configurable strict test mode also recomputes keys and projected
attributes from the payload and fails on mismatches. Production mode records a
metric and raises a typed corruption error for key mismatches.

The runtime will reject oversized items before making an AWS request. The estimate
must include attribute names, native projections, keys, and payload, with a safety
margin below DynamoDB's 400 KB item limit.

## Native Field Encoding

The v1 generator supports these native projected values. Key placeholders use the
more restrictive canonical string encoding defined above.

| Protobuf value | DynamoDB value | Notes |
| --- | --- | --- |
| `string` | `S` | Stored exactly as represented by protobuf |
| `bytes` | `B` | Raw byte value |
| Signed and unsigned integers | `N` | Base-10 integer text |
| `bool` | `BOOL` | Projection only |
| Enum | `N` | Numeric value; enum numbers must remain stable |
| Timestamp | `S` | Normalized UTC RFC 3339 for projections |
| TTL integer | `N` | Whole epoch seconds only |

Floating-point values, nested messages, repeated fields, maps, and oneofs are
payload-only in v1. DynamoDB number semantics do not exactly match protobuf
floating-point semantics, so `float` and `double` require a future explicit
encoding option before they can be projected.

Optional projected values are omitted when absent. A present protobuf default is
stored, so schemas that care about absent versus default must use explicit field
presence. ProtoJSON is not used for persistence.

## Generated API

For each annotated message, the plugin generates a repository and immutable key
and page types. The precise naming will follow the repository's Python conventions,
but the API will have this shape:

```python
class WidgetRepository:
    def get(
        self,
        key: WidgetKey,
        *,
        consistent_read: bool = False,
    ) -> Widget | None: ...

    def create(self, message: Widget) -> Widget: ...

    def put(
        self,
        message: Widget,
        *,
        expected_version: int,
    ) -> Widget: ...

    def delete(
        self,
        key: WidgetKey,
        *,
        expected_version: int | None = None,
    ) -> None: ...

    def query_by_owner(
        self,
        owner_id: str,
        *,
        limit: int = 100,
        cursor: str | None = None,
        ascending: bool = True,
    ) -> Page[Widget]: ...
```

Only declared primary-key and secondary-index access patterns generate query
methods. The generated API will not expose a general `scan` method or accept raw
filter and key expressions.

The handwritten runtime provides:

| Component | Responsibility |
| --- | --- |
| `DynamoClient` protocol | Narrow, mockable boundary around the AWS SDK client |
| `TableResolver` | Maps a logical `table_id` to a physical table name |
| `MessageCodec` | Encodes, validates, and decodes one entity mapping |
| `Repository` helpers | Shared conditional write, query, and batch behavior |
| `Page[T]` | Items and an opaque continuation cursor |
| Error types | Stable failures independent of AWS SDK exception details |

Generated repositories use composition over the runtime. They do not subclass
protobuf messages, patch generated classes, or attach global clients.

The initial Python implementation is synchronous and uses the repository's selected
AWS SDK. An asynchronous Python API can be generated later without changing
persisted data.

### Go Example

The same `src/data/example/widget/widget.proto` schema can generate an idiomatic Go
repository backed by `src/data/go/dynamodb`:

```go
type WidgetRepository interface {
	Get(
		ctx context.Context,
		key WidgetKey,
		opts GetOptions,
	) (*widgetpb.Widget, error)

	Create(
		ctx context.Context,
		message *widgetpb.Widget,
	) (*widgetpb.Widget, error)

	Put(
		ctx context.Context,
		message *widgetpb.Widget,
		expectedVersion int64,
	) (*widgetpb.Widget, error)

	Delete(
		ctx context.Context,
		key WidgetKey,
		expectedVersion *int64,
	) error

	QueryByOwner(
		ctx context.Context,
		ownerID string,
		opts QueryOptions,
	) (Page[*widgetpb.Widget], error)
}
```

Go methods accept `context.Context`, use Go protobuf message types, and return
language-specific errors that preserve the shared error categories. They use the
same key-rendering fixtures and storage compatibility tests as Python.

## Pagination

Query methods accept a bounded `limit` and return an opaque cursor derived from
DynamoDB's `LastEvaluatedKey`. The cursor includes a format version, logical entity,
index name, and encoded key. Repositories reject a cursor used with a different
entity or query method.

The cursor is a continuation token, not a durable bookmark. Its serialized format
is runtime-owned and may only change through a versioned decoder.

Filters are not a substitute for an access pattern because DynamoDB applies them
after reading matching items. Generated v1 query methods therefore do not accept
arbitrary filter expressions.

## Writes and Concurrency

An entity with a configured version field uses optimistic concurrency:

- `create` writes version `1` and requires both primary key attributes not to exist.
- `put` requires `_version` to equal `expected_version`, increments it, updates the
  protobuf field, and writes the complete item.
- `delete` can require the expected version when supplied.
- A failed condition raises `ConditionalConflict`, not a raw SDK exception.

An entity without a version field can use unconditional `put`, but opting out must
be explicit in its schema review. Generated mutable entities should normally carry
a version field.

The runtime never performs a hidden read-modify-write cycle. The caller supplies
the message and expected version. Multi-item transactions and batch writes are a
later phase and must expose DynamoDB's atomicity and retry boundaries explicitly.

## Errors

The runtime exposes stable data-layer exceptions:

| Error | Meaning |
| --- | --- |
| `ConditionalConflict` | A create, update, or delete condition failed |
| `InvalidEntity` | A message does not satisfy its declared key mapping |
| `InvalidCursor` | A pagination cursor is malformed or for another query |
| `DecodeError` | Payload metadata or protobuf bytes cannot be decoded |
| `ProjectionMismatch` | Native attributes disagree with the payload |
| `UnsupportedStorageVersion` | No reader or migration exists for the item |
| `ItemTooLarge` | The encoded item exceeds the configured size threshold |
| `DataAccessError` | Base class for mapped service and transport failures |

`get` returns `None` for a missing item. Absence is not exceptional.

## Schema Evolution

Protobuf compatibility rules still apply to payloads:

- Never reuse a field number.
- Reserve the number and name of a removed field.
- Add fields with explicit presence when absent and default have different meaning.
- Do not change a field to an incompatible wire type.
- Keep enum numbers stable and reserve removed enum values.

The DynamoDB mapping is a separate storage contract. Changing a key template,
physical key attribute, index, projected-field encoding, entity name, or protobuf
fully qualified name requires an explicit migration design.

`storage_version` tracks mapping changes, not ordinary backward-compatible protobuf
field additions. Readers may register migration functions from an older storage
version to the current message. Migration is applied in memory on read; persistence
of the upgraded item requires an explicit conditional write or a backfill job.

Index rollout follows this order:

1. Deploy readers that tolerate the new projected and index attributes.
2. Create the index through infrastructure code.
3. Dual-write the new attributes.
4. Backfill old items and verify coverage.
5. Enable generated query usage.
6. Remove old mappings only after all readers and writers have migrated.

Package or message renames require a type alias registry until old `_message_type`
values and payloads are migrated. A protobuf package rename alone is not considered
a safe persistence refactor.

## Code Generation and Bazel

Each language generator is a standard `protoc` plugin. It reads a
`CodeGeneratorRequest`, validates entity annotations, and writes its generated
files in a `CodeGeneratorResponse`. The Python plugin emits repository Python and
type stub files; the Go plugin emits repository Go files.

`src/data/python/dynamodb_codegen/defs.bzl` will expose a small Python-specific
macro named `data_access_proto_library` that composes:

- An existing application `proto_library` target.
- Python protobuf generation.
- DynamoDB repository generation.
- A Python library containing generated code and the handwritten runtime.

An application data library BUILD file should remain declarative. For example,
`src/data/example/widget/BUILD.bazel` contains:

```starlark
load(
    "//src/data/python/dynamodb_codegen:defs.bzl",
    python_data_access_proto_library = "data_access_proto_library",
)

proto_library(
    name = "widget_proto",
    srcs = ["widget.proto"],
    deps = ["//src/data/proto/dynamodb:options_proto"],
)

python_data_access_proto_library(
    name = "widget_python",
    proto = ":widget_proto",
    visibility = ["//src/example:__subpackages__"],
)
```

The same BUILD package can expose a Go repository using the Go-specific macro:

```starlark
load(
    "//src/data/go/dynamodb_codegen:defs.bzl",
    go_data_access_proto_library = "data_access_proto_library",
)

go_data_access_proto_library(
    name = "widget_go",
    proto = ":widget_proto",
    visibility = ["//src/example:__subpackages__"],
)
```

The final macros should share the underlying `proto_library` rather than compile
duplicate schema targets. Exact `rules_go` target composition will be established
in the feasibility spike.

Each macro must use the protobuf and language rules already selected by the
repository. No generated file may depend on ambient `protoc`, language toolchains,
or package-manager executables. Build and test commands use Bazelisk.

Generator output is deterministic. Golden tests compare generated source, and each
generator emits errors with protobuf file, message, and option context.

## Configuration and Security

Runtime configuration injects an SDK client and `TableResolver`. Protobuf options
contain no AWS credentials, account IDs, regions, stage names, or physical table
names.

Applications should grant repositories access only to the tables and indexes their
generated methods use. Infrastructure ownership remains outside this library, but
index names in protobuf annotations must match infrastructure declarations.

Sensitive values should not be projected merely for convenience. Binary payloads
receive DynamoDB encryption at rest, but application-level field encryption and key
management are outside v1 scope.

The runtime records operation, logical table, entity, index, consistency mode,
latency, consumed capacity when available, retry count, item size, and mapped error
type. Logs and metrics must not contain key values or payload contents by default.

## Testing Strategy

Generator tests cover:

- Valid primary and secondary key templates.
- Invalid placeholders, duplicate query names, unsupported field types, and
  reserved attributes.
- Sparse index validation.
- Deterministic generated Python and type stubs.

Codec tests cover:

- Binary round trips for every supported scalar type.
- Optional presence, enums, timestamps, TTL, and unknown protobuf fields.
- Stable key rendering and escaping rules.
- Projection and metadata mismatch detection.
- Old storage-version fixtures and registered migrations.
- Conservative item-size rejection.

Repository contract tests run against DynamoDB Local or another AWS-compatible
local server and cover:

- Create, get, update, delete, and consistent reads.
- Optimistic concurrency conflicts.
- Primary and secondary index pagination.
- Sparse indexes.
- Conditional failures and SDK error mapping.
- Old payload compatibility.

Fast unit tests may use a fake `DynamoClient`, but mocks alone are insufficient for
expression, pagination, and conditional-write behavior. Cloud integration tests can
be added for behavior DynamoDB Local does not reproduce.

## Alternatives Considered

### Existing Python ORM as the source of truth

Libraries such as PynamoDB provide a Python-native model layer, but adopting one as
the canonical schema would duplicate protobuf definitions and weaken cross-language
compatibility. Wrapping one beneath generated repositories may be reconsidered if
it materially reduces runtime code without leaking its model API.

### Store only a protobuf blob

This is simple and preserves protobuf fidelity, but it cannot support DynamoDB
queries beyond separately supplied keys. It also leaves key construction and index
projection as handwritten, repeated application logic.

### Flatten the entire message into DynamoDB attributes

This improves ad hoc visibility but creates difficult mappings for presence,
oneofs, nested messages, maps, numeric semantics, and schema evolution. Attribute
names also consume item size. V1 therefore flattens only access-critical fields.

### Add persistence methods to generated messages

Subclassing or modifying generated protobuf classes couples schemas to one Python
runtime and conflicts with protobuf generation conventions. Repositories preserve a
clean boundary and are easier to fake in tests.

## Risks and Tradeoffs

| Risk | Mitigation |
| --- | --- |
| Payload and projections can diverge | One generated encoder owns all writes; reads can validate |
| A binary payload is not queryable | Access-critical fields must be declared and projected |
| Code generation becomes custom infrastructure | Keep annotations small; golden-test all output |
| Full-message writes cost more than patches | Accept in v1; add generated targeted updates only with explicit semantics |
| Protobuf compatibility does not migrate indexes | Track `storage_version` and require rollout plans |
| DynamoDB's item limit constrains payload size | Reject early and model large content outside the item |
| Single-table key templates can become opaque | Keep templates in reviewed schemas and generate readable methods |

## Delivery Plan

### Phase 0: Feasibility spike

- Define the minimal options protobuf.
- Implement one annotated example entity.
- Generate key rendering plus `create`, `get`, `put`, and one index query.
- Prove Bazel-only code generation and Python 3.14 compatibility.
- Run repository contracts against DynamoDB Local.
- Measure generated item sizes and repository overhead.

### Phase 1: V1 runtime

- Add validation, native encodings, pagination, error mapping, and table resolution.
- Add optimistic concurrency and TTL.
- Add generator golden tests and compatibility fixtures.
- Document the schema review and index rollout checklist.
- Adopt one production entity with a bounded access-pattern set.

### Phase 2: Operational features

- Add batch get with unprocessed-key retries.
- Add explicitly modeled transactional writes.
- Add migration and backfill tooling based on registered storage versions.
- Add cloud integration tests and standard dashboards.

## V1 Acceptance Criteria

V1 is complete when:

- An annotated protobuf target produces importable Python messages and a typed
  repository using Bazelisk alone.
- No generated source is checked into the repository.
- Invalid storage annotations fail during analysis or generation with useful
  locations.
- A message round-trips through DynamoDB Local without losing protobuf presence or
  supported scalar values.
- Generated key and index queries paginate correctly and expose no raw expressions.
- Concurrent updates produce one success and one `ConditionalConflict`.
- A previous protobuf payload fixture remains readable after a compatible schema
  change.
- Projection mismatches, unsupported storage versions, malformed cursors, and
  oversized items fail with typed errors.
- `bazelisk build //...` and `bazelisk test //...` pass.

## Open Questions Before Production Adoption

- Which domain entity and access patterns should be used for the phase 0 spike?
- Will the first deployment use a shared single table or a domain-specific table?
- Which infrastructure package owns matching table and index declarations?
- Is strict projection verification affordable on every production read, or should
  it be sampled after initial rollout?

These questions do not block the library spike. They must be resolved before the
first production schema is accepted.

## References

- [Protocol Buffers proto3 language guide](https://protobuf.dev/programming-guides/proto3/)
- [Protocol Buffers field presence](https://protobuf.dev/programming-guides/field_presence/)
- [Protocol Buffers Python generated code](https://protobuf.dev/reference/python/python-generated/)
- [Protocol compiler plugin API](https://protobuf.dev/reference/cpp/api-docs/google.protobuf.compiler.plugin.pb/)
- [DynamoDB constraints](https://docs.aws.amazon.com/amazondynamodb/latest/developerguide/Constraints.html)
- [DynamoDB Query API](https://docs.aws.amazon.com/amazondynamodb/latest/APIReference/API_Query.html)
- [DynamoDB optimistic locking](https://docs.aws.amazon.com/amazondynamodb/latest/developerguide/BestPractices_OptimisticLocking.html)
- [DynamoDB filter expressions](https://docs.aws.amazon.com/amazondynamodb/latest/developerguide/Query.FilterExpression.html)
