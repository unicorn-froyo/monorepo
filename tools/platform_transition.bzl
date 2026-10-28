"""Rules for building a target for a selected platform."""

def _platform_transition_impl(_settings, attr):
    return {"//command_line_option:platforms": str(attr.platform)}

_platform_transition = transition(
    implementation = _platform_transition_impl,
    inputs = [],
    outputs = ["//command_line_option:platforms"],
)

def _platform_target_impl(ctx):
    target = ctx.attr.target[0]
    return [
        DefaultInfo(
            files = target[DefaultInfo].files,
            runfiles = target[DefaultInfo].default_runfiles,
        ),
    ]

_platform_target_rule = rule(
    implementation = _platform_target_impl,
    attrs = {
        "platform": attr.label(mandatory = True),
        "target": attr.label(
            cfg = _platform_transition,
            mandatory = True,
        ),
        "_allowlist_function_transition": attr.label(
            default = "@bazel_tools//tools/allowlists/function_transition_allowlist",
        ),
    },
)

def platform_target(name, target, platform = None, **kwargs):
    """Build a target for the matching Linux platform unless one is specified."""
    if platform == None:
        platform = select({
            "@platforms//cpu:arm64": "//tools/toolchains:aarch64_linux",
            "@platforms//cpu:x86_64": "//tools/toolchains:x86_64_linux",
        })
    _platform_target_rule(
        name = name,
        platform = platform,
        target = target,
        **kwargs
    )
