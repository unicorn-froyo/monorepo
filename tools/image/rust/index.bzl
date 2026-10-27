"""OCI images for prebuilt Rust applications."""

load("@rules_oci//oci:defs.bzl", "oci_image")

def rs_image(name, tars, entrypoint = ["/app/server"], **kwargs):
    """Create a Rust OCI image from build-time application layers."""
    oci_image(
        name = name,
        base = select({
            "@platforms//cpu:arm64": "@rust_base_linux_arm64_v8",
            "@platforms//cpu:x86_64": "@rust_base_linux_amd64",
        }),
        entrypoint = entrypoint,
        tars = tars,
        workdir = "/app",
        **kwargs
    )
