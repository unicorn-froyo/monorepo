"""OCI images for prebuilt Ruby applications."""

load("//tools/image:index.bzl", "image_with_load")

def ruby_image(name, entrypoint, tars, repo_tags, load_name = None, env = {}, **kwargs):
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
    image_with_load(
        name = name,
        base = select({
            "@platforms//cpu:arm64": "@ruby_base_linux_arm64_v8",
            "@platforms//cpu:x86_64": "@ruby_base_linux_amd64",
        }),
        entrypoint = entrypoint,
        env = image_env,
        load_name = load_name,
        repo_tags = repo_tags,
        tars = tars,
        workdir = "/app",
        **kwargs
    )
