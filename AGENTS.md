# Bazel

- Use Bazelisk.
- On macOS, install Bazelisk and OpenSSL with Homebrew.
- Store all dependency lockfiles under `third_party/`, grouped by ecosystem; never place dependency lockfiles at the repository root.
- Dependency locks belong under `third_party/{ecosystem}/` for every language ecosystem that uses a lockfile. This includes Python, Go, Ruby, Rust, and npm-managed toolchains when applicable.
- Keep ecosystem dependency manifests under `third_party/{ecosystem}/` alongside their lockfiles.
- Edit `third_party/pypi/requirements.in`, then run `bazelisk run //third_party/pypi:requirements.update`.
- Validate changes with `bazelisk build //...` and `bazelisk test //...`.
- Apply the repository's language-specific Bazel test and coverage rules uniformly, regardless of source location. Code and tests under `tools/` are not exempt from the same coverage standard as code under `src/`; extend the relevant rules when needed instead of bypassing them with lower-level test targets or location-based exclusions.
- All Bazel rules, macros, and helper starlark files must live under `tools/`. No Bazel rule or macro may be added to application directories such as `src/`, `third_party/`, or repository root packages. Language-specific rules must follow the standard tool layout: `tools/{tool}/{language}`. For example, Python coverage rules belong in `tools/coverage/python`, Ruby lint rules in `tools/lint/ruby`, and so on. Do not scatter rule implementations across ad hoc directories or repository root packages.
- Name every exported language-specific Bazel rule or macro with its established language prefix. Use the full language name for the `tools/{tool}/{language}` directory, but the prefix for the Starlark symbol:

  | Language | Directory name | Rule or macro prefix | Example |
  | --- | --- | --- | --- |
  | Go | `go` | `go_` | `go_image` |
  | Java | `java` | `java_` | `java_image` |
  | Python | `python` | `py_` | `py_coverage_test` |
  | Ruby | `ruby` | `rb_` | `rb_package` |
  | Rust | `rust` | `rs_` | `rs_coverage_test` |
  | TypeScript | `typescript` | `ts_` | `ts_lint_test` |

  Apply the prefix to new image, lint, format, test, coverage, package, and other language-specific rules and macros. Do not spell out the full language name in a rule symbol when the table defines a shorter prefix. Shared rules that are genuinely language-agnostic may use descriptive names without a language prefix. When adding a language, declare its prefix here before naming its rules.
- All build orchestration and validation must be executed through Bazel. Language-specific CI or shell pipelines are not a replacement for repository Bazel targets; they must wrap Bazel-aware targets or be represented as Bazel rules under `tools/`.
- Author Node.js tooling, runners, and executable tests in TypeScript, then compile and run them through Bazel. Do not add repository-maintained JavaScript runner source; JavaScript emitted by TypeScript compilation and JavaScript required by third-party tool configuration are allowed.

# Language integrations

- When adding a language, choose one short, unambiguous prefix and document it. Existing prefixes are `py`, `go`, `rb`, `rs`, `ts`, and `java`. Use the prefix consistently for repository-maintained public rules and macros: `{prefix}_lint_test`, `{prefix}_format_test`, `{prefix}_format_bin` (the runnable formatter), and `{prefix}_coverage_test`. Export `{prefix}_image` and/or `{prefix}_package` when the language has OCI or packaging helpers. Public macros normally live in `tools/{capability}/{language}/index.bzl`; individual BUILD target names may vary, but must call the public macro for their capability.
- Enforce static type checking through Bazel for every supported language. Use `{prefix}_typecheck_test` when ordinary Bazel builds do not already enforce it. Go, Java, Rust, and strict TypeScript builds provide type checking; Python uses a dedicated Pyright rule.
- Keep standard upstream rule names such as `go_library`, `rust_binary`, and `ts_project`. Do not wrap them just to add a repository prefix. Use the ecosystem's Bazel dependency workflows instead of adding `{prefix}_dependencies_test`, `{prefix}_dependencies_check`, or `{prefix}_dependencies_update`.
- Use the ecosystem's conventional formatter, linter, compiler or type checker, test runner, and coverage tool. State coverage metrics and thresholds explicitly; different tools do not necessarily measure the same thing. Document an intentionally unsupported capability and its rationale instead of adding a no-op rule.
- Package build outputs directly into OCI artifacts. Container startup must not compile code, install packages, or access registries. For a new language, explicitly build its manual OCI targets and verify the example service and image architecture on each supported native Linux platform when native dependencies prevent cross-compilation.

## Ruby typing

- Every Ruby source must declare `# typed: true` or a stricter Sorbet level. Do not use `# typed: false`, `# typed: ignore`, or omit the sigil.
- Run a real Sorbet check through a Bazel `rb_typecheck_test`; adding sigils without checking them does not satisfy this rule.

# Coverage

- Every language-specific `{prefix}_coverage_test` must emit `lcov.info` under `$TEST_UNDECLARED_OUTPUTS_DIR`. A console summary or tool-specific report does not replace this artifact; additional formats may be retained.
- Use workspace-relative, forward-slash paths in LCOV `SF:` entries. Exclude sandbox paths, external dependencies, generated tooling, and test sources from the measured application scope. Reject an empty report or one without the intended application sources.
- Write `lcov.info` before enforcing the shared coverage threshold, so the report survives a threshold failure. When the coverage tool can produce a report after a test failure, preserve it before propagating the failure.
- Coverage-rule tests must check that LCOV is parseable, has portable source paths, contains intended sources, and remains available on threshold failure. Test raw artifacts too when a rule promises to expose them.

# APIs

- Follow the cross-platform API standards in [`src/apis/STANDARDS.md`](src/apis/STANDARDS.md) for every supported API language and example.
