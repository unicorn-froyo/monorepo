"""Require native Linux workers when packaging the Rust server."""

load("@platforms//host:constraints.bzl", "HOST_CONSTRAINTS")

def _native_linux_binary_impl(ctx):
    host_constraints = [Label(constraint) for constraint in HOST_CONSTRAINTS]
    if ctx.attr._linux.label not in host_constraints:
        fail("Rust OCI images require a matching Linux amd64 or arm64 build worker; image builds from macOS are not supported. Native Rust builds and tests remain supported.")
    if not ctx.target_platform_has_constraint(ctx.attr._linux[platform_common.ConstraintValueInfo]):
        fail("Rust OCI images require a Linux target platform matching the Linux build worker.")
    matching_cpu = False
    for cpu in [ctx.attr._aarch64, ctx.attr._x86_64]:
        if cpu.label in host_constraints and ctx.target_platform_has_constraint(cpu[platform_common.ConstraintValueInfo]):
            matching_cpu = True
    if not matching_cpu:
        fail("Rust OCI images require matching Linux amd64 or arm64 host and target architectures; cross-compilation is not supported.")
    binary = ctx.attr.binary[DefaultInfo]
    return [DefaultInfo(files = binary.files, runfiles = binary.default_runfiles)]

native_linux_binary = rule(
    implementation = _native_linux_binary_impl,
    attrs = {
        "binary": attr.label(mandatory = True),
        "_aarch64": attr.label(default = "@platforms//cpu:aarch64"),
        "_linux": attr.label(default = "@platforms//os:linux"),
        "_x86_64": attr.label(default = "@platforms//cpu:x86_64"),
    },
)
