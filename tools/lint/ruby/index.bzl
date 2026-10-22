"""Ruby lint tests using the locked RuboCop bundle."""

load("@rules_ruby//ruby:defs.bzl", "rb_test")

def rb_lint_test(name, srcs):
    """Check Ruby sources, including test files and Rack configuration."""
    rb_test(
        name = name,
        main = "@bundle//bin:rubocop",
        args = ["--config", "$(location //tools/lint/ruby:config)"] + ["$(location %s)" % src for src in srcs],
        data = srcs + ["//tools/lint/ruby:config"],
        deps = ["@bundle"],
    )
