"""Build-time packaging for prebuilt Rust binaries."""

load("@rules_pkg//pkg:tar.bzl", "pkg_tar")

def rs_package(name, binary, package_dir = "/app", **kwargs):
    """Package a Bazel-built Rust binary without runtime compilation."""
    pkg_tar(
        name = name,
        srcs = [binary],
        mode = "0555",
        package_dir = package_dir,
        **kwargs
    )
