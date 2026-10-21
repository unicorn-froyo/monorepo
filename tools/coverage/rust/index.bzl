"""Rust coverage tests using rules_rust's LLVM instrumentation."""

load("//tools/coverage/native:index.bzl", "coverage_attrs", "coverage_impl")

def _rs_coverage_test(ctx):
    toolchain = ctx.toolchains["@rules_rust//rust:toolchain_type"]
    if not toolchain.coverage_supported:
        fail("The Rust toolchain must support LLVM coverage")
    return coverage_impl(
        ctx,
        "rust",
        llvm_cov = toolchain.llvm_cov,
        llvm_profdata = toolchain.llvm_profdata,
        tool_files = toolchain.all_files,
    )

rs_coverage_test = rule(
    implementation = _rs_coverage_test,
    attrs = coverage_attrs(),
    test = True,
    toolchains = ["@rules_rust//rust:toolchain_type"],
)
