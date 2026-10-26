---
name: add-monorepo-language
description: Add a supported programming language to this monorepo with the repository's Bazel, quality, API, coverage, and OCI conventions. Use when introducing a new language ecosystem or completing its initial repository integration; do not use for ordinary changes within an already-supported language.
---

# Add Monorepo Language

Add the language as a complete, maintainable repository integration rather than
as an isolated example. Read the root `AGENTS.md` and
`src/apis/STANDARDS.md` before making changes. Inspect the existing supported
languages and use the closest implementation as a comparator, but preserve the
new ecosystem's standard Bazel rules and tools.

## Naming contract

Choose one short, unambiguous language prefix and use it consistently. Existing
prefixes are `py`, `go`, `rb`, `rs`, and `ts`. Document a new prefix as part of
the integration.

Repository-maintained public rules and macros must use these exact names:

- `{prefix}_lint_test`
- `{prefix}_fmt_test`
- `{prefix}_fmt` for the runnable formatter
- `{prefix}_coverage_test`
- `{prefix}_image` and/or `{prefix}_package` when the integration exports
  language-level OCI or packaging helpers

Use `{prefix}_fmt_bin` only when Bazel requires a separate label for the
formatter executable. Use `{prefix}_typecheck_test` only when normal Bazel
builds do not already enforce type safety. Go, Rust, and strict TypeScript
compilation satisfy type checking through their normal build targets; Python
uses a dedicated Pyright rule. A dynamically typed language does not acquire a
type system solely for name parity.

Keep upstream rule names such as `go_library`, `rust_binary`, or `ts_project`.
Do not wrap standard rules merely to give them a repository prefix. Do not add
`{prefix}_dependencies_test`, `{prefix}_dependencies_check`, or
`{prefix}_dependencies_update`; use the dependency workflows supplied by the
ecosystem's Bazel ruleset.

Place repository rule implementations under
`tools/{capability}/{language}/`, normally exporting public macros from
`index.bzl`. Individual BUILD target names may describe their component, but
must call the consistently named public macro for that capability.

## Integration workflow

1. Inventory the comparator language's module/toolchain setup, third-party
   package, API library, tests, example service, coverage, and OCI targets.
2. Add a pinned Bazel ruleset and hermetic toolchain. Store every ecosystem
   manifest and lockfile under `third_party/{ecosystem}/`; never add a root
   lockfile.
3. Implement the naming contract above using the ecosystem's conventional
   formatter, linter, compiler or type checker, test runner, and coverage tool.
   Record coverage metrics and thresholds explicitly instead of implying that
   different tools measure identical things.
4. Add the API implementation and example service required by
   `src/apis/STANDARDS.md`. Package build outputs directly into OCI artifacts;
   do not compile code, install packages, or access registries at container
   startup.
5. Document any intentionally unsupported capability and its rationale rather
   than inventing a no-op rule for parity.

## Validation

Run focused positive and negative tests for each new rule, then run
`bazelisk build //...` and `bazelisk test //...`. Explicitly build manual OCI
targets and verify the example service and image architecture on each supported
native Linux platform when native dependencies prevent cross-compilation.
