# Polyglot Bazel rule parity

- Status: **Approved plan; implementation in progress**
- Approved: 2026-10-24
- Audience: maintainers of this repository's build rules and API examples

## Purpose

Inventory the repo's existing Bazel rule coverage, identify the gaps across Go,
Ruby, Rust, TypeScript, and Python, and close the missing repository rule
categories so each language follows the same monorepo-level contract. Deliver
work as independent pull requests so each change can be reviewed, tested, and
merged on its own.

This document defines parity at the repository rules level rather than by
matching exact tool names or implementation details. Every supported language
must provide a maintainer-supported Bazel contract for linting, formatting,
type checking, testing, coverage, and OCI packaging. The repository may use
different underlying tools per language, but it must retain the same rule
categories and success criteria across ecosystems.

This document records the assessment, selected tradeoffs, and acceptance
criteria. The linked PR descriptions, handoffs, and CI checks record current
execution status.

## Required repository rule contract

Each language in the monorepo must satisfy the same rule checklist:

- Lint rule
- Formatter rule (`py_fmt_test` for Python; equivalent formatter test rule per
  ecosystem, plus a runnable formatter binary target in Bazel for local use)
- Type-check capability, either through the normal Bazel build or a dedicated
  rule when the build does not enforce it
- Test rule
- Coverage rule
- OCI image/package rule
- Example service execution contract
- Shared API behavior and runtime expectations

The gap is that the current monorepo does not fully satisfy this checklist in
every language. The resulting work is to close those gaps across Go, Ruby,
Rust, TypeScript, and Python until each language has the same rule categories
available in the repository.

Naming pattern: repository rule names should follow the language prefix and
capability name, e.g. `py_lint_test`, `py_fmt_test`, `py_coverage_test`, and the
corresponding `rb_*`, `rs_*`, `ts_*`, and `go_*` rules for the other
ecosystems. Formatter validation rules should be named `{lang}_fmt_test`; the
corresponding runnable formatter binary should follow the same capability naming,
e.g. `{lang}_fmt` or `{lang}_fmt_bin` if a separate binary target is required.

Dependency resolution and lockfile maintenance are ecosystem workflows rather
than repository rule-parity categories. Use the canonical commands supplied by
each ecosystem's existing Bazel ruleset instead of repository-defined wrappers.

Language-specific tooling may differ: Ruff vs clang-format vs ESLint vs RuboCop,
and Pyright vs compiler-enforced checks in Go, Rust, and TypeScript. The
repository must still provide the equivalent Bazel-maintained capabilities and
enforce the same class of quality gate everywhere they are supported. A
standalone type-check rule is not required when ordinary Bazel builds already
perform the check.

## Baseline inventory

The inventory was taken at commit
[`d8fcb812`](https://github.com/unicorn-froyo/monorepo/tree/d8fcb81201eeb272ae4c81ce076d7ca8562c73cc).
Bazelisk queries identified 22 Python rule targets: eight libraries, six
binaries, two standard tests, four lint tests, and two coverage tests. The
baseline repository-wide build and all 63 tests passed.

| Capability | Python baseline | Other languages at the baseline |
| --- | --- | --- |
| Libraries, executables, and tests | `py_library`, `py_binary`, `py_test` | All have equivalents |
| Runtime and dependencies | Python 3.14, `pip.parse`, ecosystem requirements lock | All have dependency integrations and lockfiles |
| Lint | Ruff through `py_lint_test` | Go nogo; Ruby RuboCop; Rust Clippy/rustfmt; TypeScript ESLint |
| Formatter | None in the repository rule set | Rust formatting is checked; TypeScript/Go tooling has formatter workflows not uniformly standardized |
| Type checking | None in the repository rule set | Go compiler checks; Rust compiler checks; TypeScript has typed compilation; Ruby does not define an equivalent repository gate |
| Coverage in ordinary tests | unittest and coverage.py through `py_coverage_test` | All have API-base and example coverage targets |
| Service packaging | Linux-targeted executable/runfiles layer and OCI image/load targets | All have OCI examples, with different build/startup behavior |

The gaps concern how existing capabilities behave, rather than a lack of basic
language support. No language yet satisfies the full repository rule checklist.
The important distinction in this proposal is between parity work and
language-specific quality improvements. The first category is part of the
required rule contract above; the second category is only included when the
repository explicitly decides to raise every language to the same hardening bar.

In practical terms, this means the monorepo should define and implement rule
families in a consistent naming pattern across all ecosystems:
`{lang}_lint_test`, `{lang}_fmt_test`, `{lang}_fmt`, `{lang}_coverage_test`, and
the equivalent runtime/package rules for each language. When a standalone
type-check rule is required, it should be named `{lang}_typecheck_test`.

## Gap analysis

The matrix below records which repository rule categories are present at the
inventory commit for each language and, where known, the exact Bazel or tool
interfaces in use. This is the parity baseline used to scope the implementation.

| Language | Lint | Formatter | Type checking | Coverage | OCI packaging | Notes |
| --- | --- | --- | --- | --- | --- | --- |
| Python | `py_lint_test` (`ruff check`) | `py_fmt_test` (`ruff format --check`) | `py_typecheck_test` (proposed) | `py_coverage_test` (`coverage.py`) | OCI image/load targets and Linux execution packaging | Strongest baseline; also the target of explicit quality hardening |
| Go | `go_lint_test` (proposed; currently `nogo` is used but not standardized by name) | `go_fmt_test` (proposed) | Enforced by normal Go build and test targets | `go_coverage_test` | OCI examples exist; deployment behavior differs | Missing explicit rule naming |
| Ruby | `rb_lint_test` (proposed; currently `rb_lint_test` exists in wrapper-style naming but not the uniform pattern) | `rb_fmt_test` (proposed) | Intentionally out of scope; no static type system has been adopted | `rb_coverage_test` | OCI examples exist; startup installs gems and native extensions | Startup packaging path is a concrete gap |
| Rust | `rs_lint_test` (proposed; currently `clippy`/`rustfmt` are used but not standardized by name) | `rs_fmt_test` (proposed) | Enforced by normal Rust build and test targets | `rs_coverage_test` | OCI examples exist; startup rebuilds via `cargo build --release --locked` | Packaging mismatch at runtime is a concrete gap |
| TypeScript | `ts_lint_test` (wrapper exists, but naming needs to be standardized) | `ts_fmt_test` (proposed) | Enforced by strict `ts_project` builds using `tsc` | `ts_coverage_test` | OCI examples exist | Coverage wrapper flexibility gap, not a missing basic runtime rule |

This matrix makes the main difference visible: the repository already provides a
complete language runtime contract for Python and coverage wrappers, while other
ecosystems have equivalents for runtime, lint, and coverage but are uneven in
formatting. Go, Rust, and TypeScript enforce types during normal builds; Ruby has
no repository-adopted static type system.

The first four findings retain the numbering used to scope the implementation.
Source links below refer to the inventory commit so the evidence remains
available after obsolete packaging files are removed.

| Finding | Evidence and impact | Planned resolution |
| --- | --- | --- |
| 1. Rust recompiles at container startup | The [startup script](https://github.com/unicorn-froyo/monorepo/blob/d8fcb81201eeb272ae4c81ce076d7ca8562c73cc/src/apis/examples/rust/server.sh) runs `cargo build --release --locked`. The deployed executable is built separately from Bazel's executable, with startup compilation and possible registry access. | Package and execute the Bazel-built Linux server. |
| 2. Ruby installs gems at startup | The [startup script](https://github.com/unicorn-froyo/monorepo/blob/d8fcb81201eeb272ae4c81ce076d7ca8562c73cc/src/apis/examples/ruby/server.sh) runs `bundle install --local`. Cached gems reduce network needs but leave native dependency installation in the startup path. | Install gems and native extensions during the build; package the locked Bundler too. |
| 3. Coverage percentages have different guarantees | The shared 100% setting gates different metrics. Python includes branches in its coverage.py total; Ruby gates lines; TypeScript collects branches with a zero branch threshold; Go converts block profiles to lines; Rust gates LLVM lines. | Preserve existing gates and explicitly document collection and enforcement per language. |
| 4. Coverage wrappers have different flexibility | The [Ruby wrapper](https://github.com/unicorn-froyo/monorepo/blob/d8fcb81201eeb272ae4c81ce076d7ca8562c73cc/tools/coverage/ruby/index.bzl) requires one script and lacks `data`; the TypeScript wrapper accepts one entrypoint. Python already accepts multiple suites and runtime data. | Support multiple Ruby/TypeScript suites and declared runtime data while preserving existing callers. |
| P1. Python reports are not preserved as artifacts | The [Python wrapper](https://github.com/unicorn-froyo/monorepo/blob/d8fcb81201eeb272ae4c81ce076d7ca8562c73cc/tools/coverage/python/index.bzl) invokes `coverage run` and a text report without exporting LCOV or coverage data to Bazel test outputs. | Save LCOV and raw coverage data before enforcing success and thresholds. |
| P2. Python's measured source scope is loose | The [coverage configuration](https://github.com/unicorn-froyo/monorepo/blob/d8fcb81201eeb272ae4c81ce076d7ca8562c73cc/tools/coverage/python/.coveragerc) does not select application sources or exclude tests explicitly. Entirely unimported application files can escape measurement, and source errors are ignored. | Declare application source targets, include unimported files, exclude tests/tooling/external dependencies, and fail on source-analysis errors. |
| P3. Python has no formatter/type gate | The [lint rule](https://github.com/unicorn-froyo/monorepo/blob/d8fcb81201eeb272ae4c81ce076d7ca8562c73cc/tools/lint/python/index.bzl) runs Ruff `check`, without formatter or static type checks. | Add Ruff `format --check` and pinned Pyright checks through Bazel. |

## Plan to close the gaps

The implementation must close the missing repository rule categories across all
supported languages. The required work is not Python-only; it is to make each
language satisfy the same monorepo rule contract.

### Rule naming standard

The repository should standardize on the following naming pattern across
ecosystems:

Dependency locks must also live beneath `third_party/`, grouped by ecosystem, with
no lockfile stored at the repository root. The standard repository layout is:
`third_party/{ecosystem}/` for Python, Go, Ruby, Rust, npm, and any other
package manager used by the monorepo.

| Rule family | Required naming pattern |
| --- | --- |
| Lint | `{lang}_lint_test` |
| Formatter check | `{lang}_fmt_test` |
| Formatter binary | `{lang}_fmt` or `{lang}_fmt_bin` |
| Standalone type-check, when required | `{lang}_typecheck_test` |
| Coverage | `{lang}_coverage_test` |
| OCI/package | `{lang}_image`, `{lang}_package`, or equivalent |

The language prefix should match the ecosystem: `py_`, `go_`, `rb_`, `rs_`, and
`ts_`. This makes the missing rule categories visible in a single glance and
keeps new rules consistent as the repository grows.

All language-specific rule implementations must be hosted under the repository's
standard tool layout: `tools/{tool}/{language}` (Bazel label convention:
`@tools//{tool}/{language}`). All Bazel rules, macros, and helper Starlark files
must also live under `tools/`; no rule or macro may be added under application
directories like `src/`, `third_party/`, or the repository root. Build
orchestration and validation must run through Bazel rather than via
language-specific shell pipelines. Drafts should not scatter language-specific
logic across ad hoc directories or the repository root.

### Python

| Rule family | Required rule name | Exists today? | Action |
| --- | --- | --- | --- |
| Lint | `py_lint_test` | Yes | Preserve and keep as repo contract |
| Formatter check | `py_fmt_test` | No | Add `py_fmt_test` using Ruff format check |
| Formatter binary | `py_fmt` or `py_fmt_bin` | No | Add the runnable formatter binary target |
| Type-check | `py_typecheck_test` | No | Add Pyright-backed `py_typecheck_test` |
| Coverage | `py_coverage_test` | Yes | Improve source targeting and artifact preservation |
| OCI packaging | `py_image`, `py_package`, or equivalent | Yes | Preserve and validate service packaging |

### Go

| Rule family | Required rule name | Exists today? | Action |
| --- | --- | --- | --- |
| Lint | `go_lint_test` | Possibly via `nogo`, but not standardized by name | Standardize the Bazel rule naming and repo contract |
| Formatter check | `go_fmt_test` | No | Add formatter check rule |
| Formatter binary | `go_fmt` or `go_fmt_bin` | No | Add runnable formatter binary target |
| Type-check capability | Existing Go build and test targets | Yes | Preserve compiler-enforced type checking; do not add a redundant rule |
| Coverage | `go_coverage_test` | Yes, via wrapper | Preserve current behavior and document line/block handling |
| OCI packaging | `go_image`, `go_package`, or equivalent | Yes, examples exist | Validate packaging parity |

### Ruby

| Rule family | Required rule name | Exists today? | Action |
| --- | --- | --- | --- |
| Lint | `rb_lint_test` | Potentially via RuboCop wrapper, but not uniform by naming | Standardize naming and repo contract |
| Formatter check | `rb_fmt_test` | No | Add formatter parity rule |
| Formatter binary | `rb_fmt` or `rb_fmt_bin` | No | Add runnable formatter binary target |
| Type-check capability | None | Intentionally out of scope | Do not adopt a Ruby type system solely for rule-name parity |
| Coverage | `rb_coverage_test` | Yes | Improve suite/data support and coverage artifact handling |
| OCI packaging | `rb_image`, `rb_package`, or equivalent | Yes | Remove startup-time gem installation and validate OCI behavior |

### Rust

| Rule family | Required rule name | Exists today? | Action |
| --- | --- | --- | --- |
| Lint | `rs_lint_test` | Possibly via Clippy/rustfmt path, but not standardized by name | Standardize naming and repo contract |
| Formatter check | `rs_fmt_test` | Not as a distinct repo rule | Add repo-managed formatter test |
| Formatter binary | `rs_fmt` or `rs_fmt_bin` | Not as a distinct repo rule | Add runnable formatter binary target |
| Type-check capability | Existing Rust build and test targets | Yes | Preserve compiler-enforced type checking; do not add a redundant rule |
| Coverage | `rs_coverage_test` | Yes | Preserve current wrapper behavior and document gate semantics |
| OCI packaging | `rs_image`, `rs_package`, or equivalent | Yes | Package the Bazel-built server directly and remove startup rebuilds |

### TypeScript

| Rule family | Required rule name | Exists today? | Action |
| --- | --- | --- | --- |
| Lint | `ts_lint_test` | Yes via ESLint wrapper, but not fully uniform | Standardize naming and repo contract |
| Formatter check | `ts_fmt_test` | No | Add formatter rule and test |
| Formatter binary | `ts_fmt` or `ts_fmt_bin` | No | Add runnable formatter binary target |
| Type-check capability | Existing strict `ts_project` targets using `tsc` | Yes | Preserve strict compiler checking; do not add a redundant rule |
| Coverage | `ts_coverage_test` | Yes | Broaden wrapper flexibility for multiple entry points and runtime data |
| OCI packaging | `ts_image`, `ts_package`, or equivalent | Yes | Keep OCI examples aligned with repo contract |

### Execution plan

| Step | Goal | Work |
| --- | --- | --- |
| 1 | Define the repo rule contract | Record the required rule families and naming standard in the repository documentation. |
| 2 | Implement the missing rule families | Add the missing rule families above for Python, Go, Ruby, Rust, and TypeScript, one language at a time. |
| 3 | Normalize formatter and type-check behavior | Make each formatter a first-class Bazel target; add a type-check rule only where normal Bazel builds do not already enforce type safety. |
| 4 | Record deferred rules explicitly | If a language intentionally does not implement a rule, document that category as explicitly out of scope with a rationale. |
| 5 | Validate repo-wide parity | Each PR must run `bazelisk build //...`, `bazelisk test //...`, and the focused checks for the rule family it adds. |

This plan converts the current ad hoc rule coverage into a shared, explicit,
repository-owned contract across all supported languages.

## Approved decisions

- **Image build hosts:** build Rust and Ruby images on matching Linux amd64 and
  arm64 workers. Their native dependencies require more than a platform
  transition. Adding macOS-to-Linux cross-compilers is outside this work.
- **Coverage policy:** keep 100% aggregate line coverage everywhere and preserve
  Python's existing combined statement/branch gate. Make language-specific
  branch collection and enforcement explicit. No new universal branch gate is
  introduced, and existing gates are not relaxed.
- **Language quality gates:** formatter and type-checking are required parity
  capabilities where the ecosystem supports them. Compiler checking in ordinary
  Bazel builds satisfies the type-check contract without a separate rule. Ruby
  static typing is intentionally out of scope unless the repository separately
  chooses and adopts a type system.
- **Python type checker:** use Pyright from the existing npm/Bazel toolchain,
  pinned in the ecosystem lockfile, with Python 3.14 standard checking.
- **Delivery:** use five independent branches/worktrees from the inventory base,
  with up to three worker agents plus a coordinator. Each PR must pass without
  another implementation PR being merged first.
- **Scope:** actual deployment implementation, Ruby QA/prod target parity,
  broad dependency upgrades, and runtime base-image size reductions are outside
  this plan. The shared deployment rule currently prints deployment information.

## Implementation workstreams and acceptance criteria

### 1. Rust packaging

- Package the existing Bazel-built server at `/app/server`; execute it directly.
- Remove runtime Cargo compilation and obsolete source/lock packaging plumbing.
  Preserve image/load/deployment target names, manual tags, and pinned base.
- Diagnose unsupported hosts or mismatched architectures clearly.
- On both native Linux architectures, explicitly build manual image targets and
  verify `/widgets` and `/missing` with external networking disabled and a
  read-only root filesystem. Check architecture and direct entrypoint.

### 2. Ruby packaging

- Package a build-installed bundle, including native extensions, at stable
  paths. Match build/runtime Ruby version and ABI.
- Include the locked Bundler version so startup never downloads it. Remove
  startup installation and hardcoded external-repository cache paths.
- Preserve image targets and make Linux worker requirements explicit.
- On both native Linux architectures, verify native gem loading, offline
  startup, and the API contract with a read-only root and writable temporary
  storage only where required.

### 3. Shared coverage behavior

- Document line and branch behavior for every language against the approved
  policy; retain Go/Rust's executable-test wrappers.
- Load multiple Ruby scripts in order with coverage started once; support `data`.
- Accept TypeScript `entry_points` while preserving `entry_point` compatibility;
  aggregate coverage from isolated Node suites.
- Exercise multiple suites and runtime data, then deliberately fail suites and
  verify failure status and report preservation.

### 4. Python coverage

- Add explicit `source_targets` to identify the measured application dependency
  closure; migrate existing callers while retaining unittest `srcs`, `deps`, and
  `data` behavior.
- Include never-imported declared application files. Exclude tests, tooling, and
  external dependencies; reject empty source scopes and analysis errors.
- Preserve raw `.coverage` data and portable-path `lcov.info` in Bazel test
  outputs before checking test success and the existing line/branch threshold.
- Test unimported files, no application imports, exclusions, multiple suites,
  runtime data, branch-only gaps, failed tests, invalid sources, and saved reports.

### 5. Python quality

- Add reusable Ruff formatting and Pyright Bazel test rules; keep lint checks.
- Resolve types using declared Python dependencies and the hermetic interpreter.
  Enable checks for existing application and tooling packages.
- Make necessary formatting and annotation fixes, with narrowly justified
  suppressions for intentional negative tests only.
- Use real tools to test accepted/rejected formatting, valid/invalid assignments,
  and undeclared imports. Ensure the checker actually checks the requested files.

This workstream is explicitly framed as Python quality hardening within the
repository rule contract, not as proof that all languages already provide the
same static-analysis gates. If the repository later adopts a Ruby type system,
or if a compiled language's normal build stops enforcing type safety, a
standalone type-check rule should be added as an explicit follow-up with
separate acceptance criteria.

Every implementation PR runs `bazelisk build //...` and `bazelisk test //...`
alongside its focused checks. Manual image targets require explicit validation
because ordinary wildcard builds skip them. API behavior follows
[the shared standards](../../src/apis/STANDARDS.md).

## Draft PRs and progress

All five implementations have been checkpointed and pushed. The following is a
progress snapshot; use each linked draft's handoff and CI for current status.

| Workstream | Draft PR | Progress at proposal authoring |
| --- | --- | --- |
| Rust packaging | [#29 — Bazel-built Rust OCI server](https://github.com/unicorn-froyo/monorepo/pull/29) | Full build/tests and native amd64/arm64 image/startup CI passed. |
| Shared coverage | [#30 — Multiple suites and explicit coverage gates](https://github.com/unicorn-froyo/monorepo/pull/30) | Full local build and 65 tests passed; CI running. |
| Ruby packaging | [#31 — Build-installed Ruby gems](https://github.com/unicorn-froyo/monorepo/pull/31) | Full local build and 63 tests passed; native image CI failures are being investigated. |
| Python coverage | [#33 — Explicit sources and saved reports](https://github.com/unicorn-froyo/monorepo/pull/33) | Focused regressions and existing application coverage passed at 100%; full checks running. |
| Python quality | [#34 — Pyright and Ruff formatting](https://github.com/unicorn-froyo/monorepo/pull/34) | Full local build and 75 tests passed; CI running. |

## Checkpointing and independent review

Commit and push stable implementation milestones before starting long checks.
Every draft PR must retain a handoff with its branch/commit, completed checks,
pending checks, known failures, and exact resume commands. Record long-running
checks as pending until results are observed; an agent's local session ID is not
sufficient recovery information.

Each PR owns its subsystem and carries its own documentation and tests. Shared
file edits stay small. Enable the new Python quality checks for newly introduced
Python packages as those PRs merge. These merge-time adjustments do not make
the drafts depend on one another.

The main checkout remains unchanged. Each workstream can be revised or reverted
independently. Keep the drafts until their acceptance criteria and review are
complete; use CI and PR handoffs to resume any unfinished work.
