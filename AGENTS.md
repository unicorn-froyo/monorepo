# Repository conventions

- Use Bazelisk for all build orchestration and validation. Shell and
  language-specific pipelines must wrap Bazel-aware targets or be represented
  as Bazel rules under `tools/`.
- On macOS, install Bazelisk and OpenSSL through Homebrew.
- Keep dependency manifests and lockfiles under `third_party/{ecosystem}/`.
  Use the ecosystem's standard Bazel dependency workflow.
- Put all rule implementations, macros, and helper Starlark under
  `tools/{capability}/{language}/`; BUILD declarations may live with sources.
- Only `deploy_*` rules or macros may use `manual`. Use platform compatibility
  constraints for unsupported platforms.
- Write maintained Node.js tooling, runners, and executable tests in TypeScript;
  compile and run them through Bazel. Generated JavaScript and JavaScript
  required by third-party tool configuration are allowed.
- Package built outputs directly into OCI artifacts. Container startup must
  not compile code, install dependencies, or access registries.

# Language naming

Use these prefixes for repository-maintained, language-specific rules and
macros. Keep standard upstream names such as `go_library`, `rust_binary`,
and `ts_project`.

| Language | Directory | Prefix |
| --- | --- | --- |
| Go | `go` | `go_` |
| Java | `java` | `java_` |
| Python | `python` | `py_` |
| Ruby | `ruby` | `rb_` |
| Rust | `rust` | `rs_` |
| TypeScript | `typescript` | `ts_` |

Use `tools/{capability}/{language}/` for implementations, normally exporting
public macros from `index.bzl`. Shared, language-agnostic rules need no
language prefix. Add a new language's directory and short, unambiguous prefix
here before naming its rules. Use the `add-monorepo-language` skill when
introducing a language or completing its initial integration.

# Quality

- Apply each language's lint, format, type-checking, test, and coverage
  requirements equally to `src/` and `tools/`.
- Extend shared rules when necessary; do not bypass checks with lower-level
  targets or location-based exclusions.
- Use conventional ecosystem tools and explicit coverage metrics and thresholds.
  Document unsupported capabilities and their rationale instead of adding no-op checks.
- Follow `src/apis/STANDARDS.md` when changing APIs or examples.
- Every Ruby source requires `# typed: true` or stricter and a real Bazel
  `rb_typecheck_test`; do not omit sigils or use `false` or `ignore`.
- Detailed tooling and coverage contracts live in `tools/AGENTS.md` and
  `tools/coverage/AGENTS.md`; Python dependency updates follow
  `third_party/pypi/AGENTS.md`.

# Validation

- Use focused targets while iterating.
- For implementation changes, run these final gates once:
  - `bazelisk build --config=agent //...`
  - `bazelisk test --config=agent //...`
- Skip builds and tests for changes limited to documentation, agent instructions,
  or output-verbosity configuration.
- Reuse a stable Bazel cache/output location.
- Do not repeat passing checks without new changes or unresolved concerns.
  Report environmental blockers instead of retrying unchanged failures.

# Context and output

- Start with the relevant BUILD file and its loaded Starlark helpers.
- Scope searches to relevant directories. Exclude `bazel-*`, generated
  dependencies, and unrelated proposals. Avoid broad `deps(//...)` dumps.
- Search lockfiles and generated files for specific entries; avoid full reads.
- Use `--config=agent` for every Bazel build, test, and run command.
- Redirect stdout and stderr to a temporary log outside the repository.
  Report the exit status, a short summary, and the log path.
- Keep `--test_output=summary`. Use `--test_output=all`,
  `--test_output=streamed`, `--verbose_failures`, or `--subcommands` only to
  investigate a specific failure, and redirect those diagnostics too.
- On failure, inspect targeted error excerpts or the failing target's
  `bazel-testlogs/<package>/<target>/test.log`. Initially limit excerpts to
  80 lines AND 12 KB, including limiting long lines; expand only as needed.
