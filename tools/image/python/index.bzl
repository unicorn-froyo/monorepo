"""OCI images for Bazel-built Python applications."""

load("//tools/image:index.bzl", "image_with_load")

def py_image(name, tars, repo_tags, load_name = None, entrypoint = ["/app/server"], **kwargs):
    """Create a Python image and its local load target."""
    image_with_load(
        name = name,
        base = select({
            "@platforms//cpu:arm64": "@python_base_linux_arm64_v8",
            "@platforms//cpu:x86_64": "@python_base_linux_amd64",
        }),
        entrypoint = entrypoint,
        load_name = load_name,
        repo_tags = repo_tags,
        tars = tars,
        **kwargs
    )
