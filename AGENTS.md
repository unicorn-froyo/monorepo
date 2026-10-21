# Bazel

- Use Bazelisk.
- On macOS, install Bazelisk and OpenSSL with Homebrew.
- Store all dependency lockfiles under `third_party/`, grouped by ecosystem; never place dependency lockfiles at the repository root.
- Edit `third_party/pypi/requirements.in`, then run `bazelisk run //third_party/pypi:requirements.update`.
- Validate changes with `bazelisk build //...` and `bazelisk test //...`.

# APIs

- Follow the cross-platform API standards in [`src/apis/STANDARDS.md`](src/apis/STANDARDS.md) for every supported API language and example.
