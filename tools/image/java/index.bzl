"""OCI images for Bazel-built Java applications."""

load("@rules_oci//oci:defs.bzl", "oci_image")
load("@rules_pkg//pkg:tar.bzl", "pkg_tar")

def java_image(name, binary, entrypoint, **kwargs):
    """Package a Java binary and its resolved runtime classpath at build time."""
    pkg_tar(
        name = name + "_application_layer",
        srcs = [binary],
        include_runfiles = True,
        mode = "0555",
        package_dir = "/app",
    )
    oci_image(
        name = name,
        base = select({
            "@platforms//cpu:arm64": "@java_base_linux_arm64_v8",
            "@platforms//cpu:x86_64": "@java_base_linux_amd64",
        }),
        entrypoint = [entrypoint],
        tars = [name + "_application_layer"],
        workdir = "/app",
        **kwargs
    )
