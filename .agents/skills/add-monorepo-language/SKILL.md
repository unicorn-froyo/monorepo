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

## Integration workflow

1. Inventory the comparator language's module/toolchain setup, third-party
   package, API library, tests, example service, coverage, and OCI targets.
2. Add a pinned Bazel ruleset and hermetic toolchain.
3. Implement the language rules and coverage contract in `AGENTS.md`. Use the
   comparator's rule tests as a starting point for the new integration.
4. Add the API implementation and example service required by
   `src/apis/STANDARDS.md`.

## Validation

Run focused positive and negative tests for each new rule, then run
the repository-wide Bazel build and test gates in `AGENTS.md`.
