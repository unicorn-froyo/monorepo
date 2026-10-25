# Python and polyglot Bazel rule parity

- Status: **Approved plan; implementation in progress**
- Approved: 2026-10-24
- Audience: maintainers of this repository's build rules and API examples

## Purpose

Use the Python rules as an inventory baseline, identify meaningful capability
gaps across Go, Ruby, Rust, and TypeScript, and address weaknesses in Python's
own coverage and quality checks. Deliver the work as independent pull requests
so each change can be reviewed, tested, and merged on its own.

This document records the assessment, selected tradeoffs, and acceptance
criteria. The linked PR descriptions, handoffs, and CI checks record current
execution status.

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
| Dependency maintenance | `requirements.update` and `requirements.test` | No equivalent repository-defined update/check targets |
| Lint | Ruff through `py_lint_test` | Go nogo; Ruby RuboCop; Rust Clippy/rustfmt; TypeScript ESLint |
| Coverage in ordinary tests | unittest and coverage.py through `py_coverage_test` | All have API-base and example coverage targets |
| Service packaging | Linux-targeted executable/runfiles layer and OCI image/load targets | All have OCI examples, with different build/startup behavior |
| Python formatting and types | Ruff lint only | Rust already checks formatting; compiled languages have compiler type checks |

The gaps concern how existing capabilities behave, rather than a lack of basic
language support.

## Gap analysis

The first five findings retain the numbering used to scope the implementation.
Source links below refer to the inventory commit so the evidence remains
available after obsolete packaging files are removed.

| Finding | Evidence and impact | Planned resolution |
| --- | --- | --- |
| 1. Rust recompiles at container startup | The [startup script](https://github.com/unicorn-froyo/monorepo/blob/d8fcb81201eeb272ae4c81ce076d7ca8562c73cc/src/apis/examples/rust/server.sh) runs `cargo build --release --locked`. The deployed executable is built separately from Bazel's executable, with startup compilation and possible registry access. | Package and execute the Bazel-built Linux server. |
| 2. Ruby installs gems at startup | The [startup script](https://github.com/unicorn-froyo/monorepo/blob/d8fcb81201eeb272ae4c81ce076d7ca8562c73cc/src/apis/examples/ruby/server.sh) runs `bundle install --local`. Cached gems reduce network needs but leave native dependency installation in the startup path. | Install gems and native extensions during the build; package the locked Bundler too. |
| 3. Dependency maintenance is inconsistent | Python's [dependency BUILD](https://github.com/unicorn-froyo/monorepo/blob/d8fcb81201eeb272ae4c81ce076d7ca8562c73cc/third_party/pypi/BUILD.bazel) exposes an update and test workflow. The other ecosystems expose dependencies without equivalent maintenance targets. | Add consistent offline metadata tests and explicit full-resolution check/update commands. |
| 4. Coverage percentages have different guarantees | The shared 100% setting gates different metrics. Python includes branches in its coverage.py total; Ruby gates lines; TypeScript collects branches with a zero branch threshold; Go converts block profiles to lines; Rust gates LLVM lines. | Preserve existing gates and explicitly document collection and enforcement per language. |
| 5. Coverage wrappers have different flexibility | The [Ruby wrapper](https://github.com/unicorn-froyo/monorepo/blob/d8fcb81201eeb272ae4c81ce076d7ca8562c73cc/tools/coverage/ruby/index.bzl) requires one script and lacks `data`; the TypeScript wrapper accepts one entrypoint. Python already accepts multiple suites and runtime data. | Support multiple Ruby/TypeScript suites and declared runtime data while preserving existing callers. |
| P1. Python reports are not preserved as artifacts | The [Python wrapper](https://github.com/unicorn-froyo/monorepo/blob/d8fcb81201eeb272ae4c81ce076d7ca8562c73cc/tools/coverage/python/index.bzl) invokes `coverage run` and a text report without exporting LCOV or coverage data to Bazel test outputs. | Save LCOV and raw coverage data before enforcing success and thresholds. |
| P2. Python's measured source scope is loose | The [coverage configuration](https://github.com/unicorn-froyo/monorepo/blob/d8fcb81201eeb272ae4c81ce076d7ca8562c73cc/tools/coverage/python/.coveragerc) does not select application sources or exclude tests explicitly. Entirely unimported application files can escape measurement, and source errors are ignored. | Declare application source targets, include unimported files, exclude tests/tooling/external dependencies, and fail on source-analysis errors. |
| P3. Python has no formatter/type gate | The [lint rule](https://github.com/unicorn-froyo/monorepo/blob/d8fcb81201eeb272ae4c81ce076d7ca8562c73cc/tools/lint/python/index.bzl) runs Ruff `check`, without formatter or static type checks. | Add Ruff `format --check` and pinned Pyright checks through Bazel. |

## Approved decisions

- **Image build hosts:** build Rust and Ruby images on matching Linux amd64 and
  arm64 workers. Their native dependencies require more than a platform
  transition. Adding macOS-to-Linux cross-compilers is outside this work.
- **Coverage policy:** keep 100% aggregate line coverage everywhere and preserve
  Python's existing combined statement/branch gate. Make language-specific
  branch collection and enforcement explicit. No new universal branch gate is
  introduced, and existing gates are not relaxed.
- **Dependency validation:** ordinary tests check manifest/direct-lock
  consistency offline. Explicit commands can access registries to reproduce
  resolution in scratch. Full resolution is not claimed by the offline tests.
- **Python type checker:** use Pyright from the existing npm/Bazel toolchain,
  pinned in the ecosystem lockfile, with Python 3.14 standard checking.
- **Delivery:** use six independent branches/worktrees from the inventory base,
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

### 3. Dependency maintenance

- Add `dependencies.test`, `dependencies.check`, and `dependencies.update` under
  each Go, npm, Ruby, and Rust dependency package. Keep Python's requirements
  workflow unchanged.
- Use pinned tools and scratch directories. Updates preserve compatible locked
  versions and copy back only declared outputs; checks never modify the checkout.
- Stage Go sources beneath the temporary module root before tidy. Maintain
  Rust's Bazel dependency lock separately from runtime Cargo packaging cleanup.
- Test direct-requirement drift, missing resolutions/checksums, scratch
  isolation, write boundaries, and supported Cargo version requirements. Verify
  explicit full checks leave synchronized locks unchanged.

### 4. Shared coverage behavior

- Document line and branch behavior for every language against the approved
  policy; retain Go/Rust's executable-test wrappers.
- Load multiple Ruby scripts in order with coverage started once; support `data`.
- Accept TypeScript `entry_points` while preserving `entry_point` compatibility;
  aggregate coverage from isolated Node suites.
- Exercise multiple suites and runtime data, then deliberately fail suites and
  verify failure status and report preservation.

### 5. Python coverage

- Add explicit `source_targets` to identify the measured application dependency
  closure; migrate existing callers while retaining unittest `srcs`, `deps`, and
  `data` behavior.
- Include never-imported declared application files. Exclude tests, tooling, and
  external dependencies; reject empty source scopes and analysis errors.
- Preserve raw `.coverage` data and portable-path `lcov.info` in Bazel test
  outputs before checking test success and the existing line/branch threshold.
- Test unimported files, no application imports, exclusions, multiple suites,
  runtime data, branch-only gaps, failed tests, invalid sources, and saved reports.

### 6. Python quality

- Add reusable Ruff formatting and Pyright Bazel test rules; keep lint checks.
- Resolve types using declared Python dependencies and the hermetic interpreter.
  Enable checks for existing application and tooling packages.
- Make necessary formatting and annotation fixes, with narrowly justified
  suppressions for intentional negative tests only.
- Use real tools to test accepted/rejected formatting, valid/invalid assignments,
  and undeclared imports. Ensure the checker actually checks the requested files.

Every implementation PR runs `bazelisk build //...` and `bazelisk test //...`
alongside its focused checks. Manual image targets require explicit validation
because ordinary wildcard builds skip them. API behavior follows
[the shared standards](../../src/apis/STANDARDS.md).

## Draft PRs and progress

All six implementations have been checkpointed and pushed. The following is a
progress snapshot; use each linked draft's handoff and CI for current status.

| Workstream | Draft PR | Progress at proposal authoring |
| --- | --- | --- |
| Rust packaging | [#29 — Bazel-built Rust OCI server](https://github.com/unicorn-froyo/monorepo/pull/29) | Full build/tests and native amd64/arm64 image/startup CI passed. |
| Shared coverage | [#30 — Multiple suites and explicit coverage gates](https://github.com/unicorn-froyo/monorepo/pull/30) | Full local build and 65 tests passed; CI running. |
| Ruby packaging | [#31 — Build-installed Ruby gems](https://github.com/unicorn-froyo/monorepo/pull/31) | Full local build and 63 tests passed; native image CI failures are being investigated. |
| Dependency maintenance | [#32 — Ecosystem maintenance workflows](https://github.com/unicorn-froyo/monorepo/pull/32) | Full local build and 70 tests passed; all four full-resolution checks passed. Reviewed comparator follow-ups also pass focused checks. |
| Python coverage | [#33 — Explicit sources and saved reports](https://github.com/unicorn-froyo/monorepo/pull/33) | Focused regressions and existing application coverage passed at 100%; full checks running. |
| Python quality | [#34 — Pyright and Ruff formatting](https://github.com/unicorn-froyo/monorepo/pull/34) | Full local build and 75 tests passed; CI running. |

## Checkpointing and independent review

Commit and push stable implementation milestones before starting long checks.
Every draft PR must retain a handoff with its branch/commit, completed checks,
pending checks, known failures, and exact resume commands. Record long-running
checks as pending until results are observed; an agent's local session ID is not
sufficient recovery information.

Each PR owns its subsystem and carries its own documentation and tests. Shared
file edits stay small. The Python-quality and dependency PRs independently add
the same pnpm extension; retain one block when both are merged. Enable the new
Python quality checks for newly introduced Python packages as those PRs meet.
These merge-time adjustments do not make either draft depend on the other.

The main checkout remains unchanged. Each workstream can be revised or reverted
independently. Keep the drafts until their acceptance criteria and review are
complete; use CI and PR handoffs to resume any unfinished work.
