"""OCI images for prebuilt Ruby applications."""

load("@rules_oci//oci:defs.bzl", "oci_image")

def rb_image(name, entrypoint, tars, env = {}, **kwargs):
    """Create a Ruby OCI image from build-time application and gem layers."""
    image_env = {
        "BUNDLE_DISABLE_SHARED_GEMS": "true",
        "BUNDLE_FROZEN": "true",
        "BUNDLE_GEMFILE": "/app/third_party/ruby/Gemfile",
        "BUNDLE_IGNORE_CONFIG": "true",
        "BUNDLE_PATH": "/usr/local/bundle",
        "GEM_HOME": "/usr/local/bundle/ruby/4.0.0",
        "GEM_PATH": "/usr/local/bundle/ruby/4.0.0",
        "RAILS_ENV": "production",
    }
    image_env.update(env)
    oci_image(
        name = name,
        base = select({
            "@platforms//cpu:arm64": "@ruby_base_linux_arm64_v8",
            "@platforms//cpu:x86_64": "@ruby_base_linux_amd64",
        }),
        entrypoint = entrypoint,
        env = image_env,
        tars = tars,
        workdir = "/app",
        **kwargs
    )
