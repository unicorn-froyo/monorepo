"""OCI images for prebuilt Rust applications."""

load("//tools/image:index.bzl", "image_with_load")

def rs_image(name, tars, repo_tags, load_name = None, entrypoint = ["/app/server"], **kwargs):
    """Create a Rust OCI image from build-time application layers."""
    image_with_load(
        name = name,
        base = select({
            "@platforms//cpu:arm64": "@rust_base_linux_arm64_v8",
            "@platforms//cpu:x86_64": "@rust_base_linux_amd64",
        }),
        entrypoint = entrypoint,
        load_name = load_name,
        repo_tags = repo_tags,
        tars = tars,
        workdir = "/app",
        **kwargs
    )
