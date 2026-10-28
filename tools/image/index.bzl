"""Create an OCI image and its matching local load target."""

load("@rules_oci//oci:defs.bzl", "oci_image", "oci_load")

def image_with_load(name, repo_tags, load_name = None, **kwargs):
    """Define an image and a load target with the same tags and compatibility."""
    oci_image(name = name, **kwargs)
    oci_load(
        name = load_name or name + "_load",
        image = ":" + name,
        repo_tags = repo_tags,
        tags = kwargs.get("tags", []),
        target_compatible_with = kwargs.get("target_compatible_with", []),
    )
