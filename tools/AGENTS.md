# Language tooling

- Follow the language naming table in the root `AGENTS.md`.
- Export public macros from `tools/{capability}/{language}/index.bzl` normally.
  BUILD targets must call the public macro for their capability.
- Provide `{prefix}_lint_test`, `{prefix}_format_test`, `{prefix}_format_bin`,
  and `{prefix}_coverage_test`; provide `{prefix}_image` and/or
  `{prefix}_package` when supported.
- Enforce static typing through Bazel. Use `{prefix}_typecheck_test` when
  ordinary builds do not enforce it. Go, Java, Rust, and strict TypeScript
  builds enforce typing; Python uses a dedicated Pyright rule.
- Keep standard upstream names such as `go_library`, `rust_binary`, and
  `ts_project`; do not wrap them merely to add a prefix.
- Use ecosystem Bazel dependency workflows rather than adding
  `{prefix}_dependencies_test`, `{prefix}_dependencies_check`, or
  `{prefix}_dependencies_update`.
- Use conventional ecosystem tools, explicit coverage metrics and thresholds,
  and documented rationales for unsupported capabilities; do not add no-op rules.
