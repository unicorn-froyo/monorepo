"""Checksum-pinned, relocatable PostgreSQL distributions for sandboxed tests."""

def _postgresql_repository_impl(ctx):
    artifact = "embedded-postgres-binaries-" + ctx.attr.platform
    ctx.download_and_extract(
        url = "https://repo.maven.apache.org/maven2/io/zonky/test/postgres/{artifact}/17.10.0/{artifact}-17.10.0.jar".format(artifact = artifact),
        sha256 = ctx.attr.sha256,
        type = "zip",
        output = "archive",
    )
    ctx.extract(ctx.path("archive/" + ctx.attr.archive), output = "postgresql")
    ctx.delete("archive")
    ctx.file("BUILD.bazel", """package(default_visibility = ["//visibility:public"])
exports_files(["postgresql/bin/initdb", "postgresql/bin/postgres"])
filegroup(name = "distribution", srcs = glob(["postgresql/**"]))
""")

_postgresql_repository = repository_rule(
    implementation = _postgresql_repository_impl,
    attrs = {
        "platform": attr.string(mandatory = True),
        "sha256": attr.string(mandatory = True),
        "archive": attr.string(mandatory = True),
    },
)

def _distributions(_ctx):
    for platform, sha256, archive in [
        ("darwin-amd64", "667a0eea70157656649417777af452148f6c79ae3654b2cd057a37fd701bd9e9", "postgres-darwin-x86_64.txz"),
        ("darwin-arm64v8", "b8c73288326af937b632208110b1d629c404ebef7519f8bcc7fd72404c68a36a", "postgres-darwin-arm_64.txz"),
        ("linux-amd64", "a6c44794a7a258621b8cb98c196bf621cdd705d9fa73c3628166b658c419877a", "postgres-linux-x86_64.txz"),
        ("linux-arm64v8", "47aa73724470a8bdb5e68e3978c1f07c577ab7a5c23b97b84f99d7e165f4876f", "postgres-linux-arm_64.txz"),
    ]:
        _postgresql_repository(
            name = "postgresql_" + platform.replace("-", "_"),
            platform = platform,
            sha256 = sha256,
            archive = archive,
        )

postgresql = module_extension(implementation = _distributions)
