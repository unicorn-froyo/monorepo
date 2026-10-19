"""index.bzl provides the packaging ruleset"""

load("@rules_python//python:defs.bzl", "PyInfo")
load("//tools:providers.bzl", "PackageInfo")
load("//tools:utils.bzl", "get_transitive_deps")

_SUPPORTED_RUNTIMES = ["python", "ruby"]

def _runtime_and_sources(ctx):
    """Determine the package runtime and collect its transitive sources."""
    runtime = ctx.attr.runtime
    if runtime == "auto":
        if all([PyInfo in target for target in ctx.attr.srcs]):
            runtime = "python"
        elif any([
            source.extension == "rb"
            for target in ctx.attr.srcs
            for source in target.files.to_list()
        ]):
            runtime = "ruby"
        else:
            fail("Unable to determine package runtime; set runtime explicitly")

    if runtime == "python":
        for target in ctx.attr.srcs:
            if PyInfo not in target:
                fail("Python package sources must provide PyInfo")
        return runtime, get_transitive_deps(ctx.attr.srcs)

    # Ruby rules expose their transitive sources through DefaultInfo. Keeping
    # this rule independent of rules_ruby's private provider API also allows
    # filegroups containing Ruby sources to be packaged.
    return runtime, ctx.files.srcs

def _package_api(ctx):
    if not ctx.attr.srcs:
        fail("At least one source target is required")

    language, source_files = _runtime_and_sources(ctx)
    output_file = ctx.actions.declare_file(ctx.attr.name + ".zip")
    files = ctx.files._packaging_bin + ctx.files._python_bin + source_files + ctx.files.data
    args = ctx.actions.args()
    args.add_joined([source.path for source in source_files], join_with = ",")
    args.add("--output-file", output_file.path)
    args.add("--runtime", language)
    ctx.actions.run(
        mnemonic = "Packaging",
        executable = ctx.executable._packaging_bin,
        arguments = [args],
        inputs = files,
        outputs = [output_file],
    )

    return [
        DefaultInfo(
            files = depset([output_file]),
        ),
        PackageInfo(language = language),
    ]

package_api = rule(
    implementation = _package_api,
    attrs = {
        "srcs": attr.label_list(),
        "data": attr.label_list(
            allow_files = True,
        ),
        "runtime": attr.string(
            default = "auto",
            doc = "Runtime to package. By default it is inferred from the sources.",
            values = ["auto"] + _SUPPORTED_RUNTIMES,
        ),
        "_packaging_bin": attr.label(
            default = "//tools/package:package_api_bin",
            executable = True,
            cfg = "exec",
        ),
        "_python_bin": attr.label(
            default = "@python_interpreter//:python_bin",
            executable = True,
            cfg = "exec",
            allow_files = True,
        ),
    },
)
