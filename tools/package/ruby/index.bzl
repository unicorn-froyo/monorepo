"""Build-time packaging for installed Ruby bundles."""

load("@rules_pkg//pkg:mappings.bzl", "REMOVE_BASE_DIRECTORY", "pkg_files", "strip_prefix")
load("@rules_pkg//pkg:tar.bzl", "pkg_tar")

def rb_package(name, bundle = "@bundle", target_compatible_with = []):
    """Package a Bazel-installed Ruby bundle without startup installation."""
    native.filegroup(
        name = name + "_gems",
        srcs = [bundle],
        output_group = "gems",
        target_compatible_with = target_compatible_with,
    )
    pkg_files(
        name = name + "_files",
        srcs = [name + "_gems"],
        prefix = "/usr/local/bundle",
        renames = {name + "_gems": REMOVE_BASE_DIRECTORY},
        target_compatible_with = target_compatible_with,
    )
    pkg_files(
        name = name + "_bundler_files",
        srcs = ["@bundle//:bundler-2.6.9"],
        excludes = ["@bundle//:third_party/ruby/vendor/cache/bundler-2.6.9.gem"],
        prefix = "/usr/local/bundle/ruby/4.0.0",
        strip_prefix = strip_prefix.from_root("bundler-2.6.9"),
        target_compatible_with = target_compatible_with,
    )
    pkg_tar(
        name = name,
        srcs = [
            name + "_bundler_files",
            name + "_files",
        ],
        target_compatible_with = target_compatible_with,
    )
