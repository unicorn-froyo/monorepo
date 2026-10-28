"""OCI images for Bazel-built TypeScript applications."""

load("//tools/image:index.bzl", "image_with_load")

def typescript_image(name, tars, entrypoint, repo_tags, load_name = None, **kwargs):
    """Create a Node.js image and its local load target."""
    image_with_load(
        name = name,
        base = select({
            "@platforms//cpu:arm64": "@node_base_linux_arm64_v8",
            "@platforms//cpu:x86_64": "@node_base_linux_amd64",
        }),
        entrypoint = entrypoint,
        load_name = load_name,
        repo_tags = repo_tags,
        tars = tars,
        workdir = "/app",
        **kwargs
    )
