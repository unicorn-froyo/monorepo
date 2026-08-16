# Bazel

- Use Bazelisk.
- On macOS, install Bazelisk and OpenSSL with Homebrew.
- Edit `third_party/pypi/requirements.in`, then run `bazelisk run //third_party/pypi:requirements.update`.
- Validate changes with `bazelisk build //...` and `bazelisk test //...`.
