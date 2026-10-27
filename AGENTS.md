# Bazel

- Use Bazelisk.
- On macOS, install Bazelisk and OpenSSL with Homebrew.
- Store all dependency lockfiles under `third_party/`, grouped by ecosystem; never place dependency lockfiles at the repository root.
- Dependency locks belong under `third_party/{ecosystem}/` for every language ecosystem that uses a lockfile. This includes Python, Go, Ruby, Rust, and npm-managed toolchains when applicable.
- Edit `third_party/pypi/requirements.in`, then run `bazelisk run //third_party/pypi:requirements.update`.
- Validate changes with `bazelisk build //...` and `bazelisk test //...`.
- Apply the repository's language-specific Bazel test and coverage rules uniformly, regardless of source location. Code and tests under `tools/` are not exempt from the same coverage standard as code under `src/`; extend the relevant rules when needed instead of bypassing them with lower-level test targets or location-based exclusions.
- All Bazel rules, macros, and helper starlark files must live under `tools/`. No Bazel rule or macro may be added to application directories such as `src/`, `third_party/`, or repository root packages. Language-specific rules must follow the standard tool layout: `tools/{tool}/{language}`. For example, Python coverage rules belong in `tools/coverage/python`, Ruby lint rules in `tools/lint/ruby`, and so on. Do not scatter rule implementations across ad hoc directories or repository root packages.
- All build orchestration and validation must be executed through Bazel. Language-specific CI or shell pipelines are not a replacement for repository Bazel targets; they must wrap Bazel-aware targets or be represented as Bazel rules under `tools/`.
- Author Node.js tooling, runners, and executable tests in TypeScript, then compile and run them through Bazel. Do not add repository-maintained JavaScript runner source; JavaScript emitted by TypeScript compilation and JavaScript required by third-party tool configuration are allowed.
- Author Node.js tooling, runners, and executable tests in TypeScript, then compile and run them through Bazel. Do not add repository-maintained JavaScript runner source; JavaScript emitted by TypeScript compilation and JavaScript required by third-party tool configuration are allowed.

# APIs

- Follow the cross-platform API standards in [`src/apis/STANDARDS.md`](src/apis/STANDARDS.md) for every supported API language and example.
