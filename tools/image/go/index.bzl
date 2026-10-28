"""OCI images for Bazel-built Go applications."""

load("//tools/image:index.bzl", "image_with_load")

def go_image(name, tars, repo_tags, load_name = None, entrypoint = ["/app/server"], **kwargs):
    """Create a Linux Go image and its local load target."""
    image_with_load(
        name = name,
        architecture = select({
            "@platforms//cpu:arm64": "arm64",
            "@platforms//cpu:x86_64": "amd64",
        }),
        entrypoint = entrypoint,
        load_name = load_name,
        os = "linux",
        repo_tags = repo_tags,
        tars = tars,
        **kwargs
    )
