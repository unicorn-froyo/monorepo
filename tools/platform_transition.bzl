"""Rules for building a target for an explicit platform."""

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

platform_target = rule(
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
