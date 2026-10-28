"""OCI images for Bazel-built Java applications."""

load("@rules_pkg//pkg:tar.bzl", "pkg_tar")
load("//tools/image:index.bzl", "image_with_load")

def java_image(name, binary, entrypoint, repo_tags, load_name = None, **kwargs):
    """Package a Java binary and its resolved runtime classpath at build time."""
    pkg_tar(
        name = name + "_application_layer",
        srcs = [binary],
        include_runfiles = True,
        mode = "0555",
        package_dir = "/app",
    )
    image_with_load(
        name = name,
        base = select({
            "@platforms//cpu:arm64": "@java_base_linux_arm64_v8",
            "@platforms//cpu:x86_64": "@java_base_linux_amd64",
        }),
        entrypoint = [entrypoint],
        load_name = load_name,
        repo_tags = repo_tags,
        tars = [name + "_application_layer"],
        workdir = "/app",
        **kwargs
    )
