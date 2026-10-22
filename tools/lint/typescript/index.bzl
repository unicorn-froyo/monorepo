"""TypeScript source linting with ESLint."""

load("@npm//third_party/npm:eslint/package_json.bzl", "bin")

def ts_lint_test(name, srcs):
    """Lint the given TypeScript source and test files."""
    bin.eslint_test(
        name = name,
        data = srcs + [
            "//tools/lint/typescript:config",
            "//third_party/npm:node_modules/@eslint/js",
            "//third_party/npm:node_modules/typescript-eslint",
        ],
        args = ["--config", "$(rootpath //tools/lint/typescript:config)", "--max-warnings=0"] + ["$(rootpath %s)" % src for src in srcs],
    )
