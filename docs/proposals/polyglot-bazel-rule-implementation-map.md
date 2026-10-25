# Polyglot Bazel Rule Parity Implementation Map

**Proposal:** [Polyglot Bazel rule parity](polyglot-bazel-rule-parity.md)  
**Status snapshot:** 2026-10-24

This map tracks delivery of the proposal's six implementation workstreams. The
proposal remains authoritative for scope and acceptance criteria; PRs and their
checks are authoritative for the latest execution status.

| Proposal workstream | PR | Implementation status |
| --- | --- | --- |
| [1. Rust packaging](polyglot-bazel-rule-parity.md#1-rust-packaging) | [#29](https://github.com/unicorn-froyo/monorepo/pull/29) | Open, non-draft. Bazel, Docker, amd64, and arm64 checks pass; branch is behind `main`. |
| [2. Ruby packaging](polyglot-bazel-rule-parity.md#2-ruby-packaging) | [#31](https://github.com/unicorn-froyo/monorepo/pull/31) | Draft. Bazel and Docker checks pass; amd64 and arm64 image checks fail and need follow-up; branch is behind `main`. |
| [3. Dependency maintenance](polyglot-bazel-rule-parity.md#3-dependency-maintenance) | [#32](https://github.com/unicorn-froyo/monorepo/pull/32) | Draft. Bazel build and test check pass; branch is behind `main`. |
| [4. Shared coverage behavior](polyglot-bazel-rule-parity.md#4-shared-coverage-behavior) | [#30](https://github.com/unicorn-froyo/monorepo/pull/30) | Draft. Bazel build and test check pass; branch is behind `main`. |
| [5. Python coverage](polyglot-bazel-rule-parity.md#5-python-coverage) | [#33](https://github.com/unicorn-froyo/monorepo/pull/33) | Implementation and local acceptance checks complete on main-integrated commit `fc67ff4`. Focused checks, full build, and all 76 tests pass; GitHub CI passes. Draft pending review. |
| [6. Python quality](polyglot-bazel-rule-parity.md#6-python-quality) | [#34](https://github.com/unicorn-froyo/monorepo/pull/34) | Merged; Bazel build and test check pass. |

For Python coverage, completion means the measured source set comes from
declared `source_targets`, unimported application files count, tests/tooling/
external dependencies are excluded, and LCOV plus raw coverage data are saved
before test or threshold failures. The focused regression suite verifies those
cases, including empty or invalid source scopes and report preservation.
