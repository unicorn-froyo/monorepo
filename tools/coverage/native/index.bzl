"""Shared support for coverage that runs under ordinary `bazel test`."""

load("//tools/coverage:config.bzl", "MINIMUM_LINE_COVERAGE")

def _instrument_impl(_settings, _attr):
    return {
        "//command_line_option:collect_code_coverage": True,
        "//command_line_option:instrumentation_filter": "//src/apis[/:]",
    }

instrumented = transition(
    implementation = _instrument_impl,
    inputs = [],
    outputs = [
        "//command_line_option:collect_code_coverage",
        "//command_line_option:instrumentation_filter",
    ],
)

def _instrument_rust_impl(settings, attr):
    result = _instrument_impl(settings, attr)

    # Linux needs the profiler runtime initialized by the test executable,
    # not just coverage instrumentation in its library dependencies.
    result["//command_line_option:instrument_test_targets"] = True
    return result

rust_instrumented = transition(
    implementation = _instrument_rust_impl,
    inputs = [],
    outputs = [
        "//command_line_option:collect_code_coverage",
        "//command_line_option:instrumentation_filter",
        "//command_line_option:instrument_test_targets",
    ],
)

def coverage_attrs(rust = False):
    """Attributes shared by native-language coverage tests."""
    return {
        "target": attr.label(executable = True, cfg = rust_instrumented if rust else instrumented, mandatory = True),
        "_runner": attr.label(
            default = "//tools/coverage/native:coverage_bin",
            executable = True,
            cfg = "target",
        ),
        "_allowlist_function_transition": attr.label(
            default = "@bazel_tools//tools/allowlists/function_transition_allowlist",
        ),
    }

def coverage_impl(ctx, language, llvm_cov = None, llvm_profdata = None, tool_files = None):
    """Run the instrumented dependency and preserve its runtime dependencies."""
    target = ctx.attr.target[0]
    executable = target[DefaultInfo].files_to_run.executable
    environment = target[RunEnvironmentInfo].environment if RunEnvironmentInfo in target else {}
    args = [language, executable.short_path, json.encode(environment), str(MINIMUM_LINE_COVERAGE)]
    files = [executable]
    if llvm_cov:
        args += [llvm_cov.short_path, llvm_profdata.short_path]
        files += [llvm_cov, llvm_profdata]
    script = ctx.actions.declare_file(ctx.label.name + ".sh")
    ctx.actions.write(
        script,
        "#!/bin/sh\nset -eu\nexec '%s' %s\n" % (
            ctx.executable._runner.short_path,
            " ".join(["'%s'" % arg.replace("'", "'\\''") for arg in args]),
        ),
        is_executable = True,
    )
    runfiles = ctx.runfiles(files = files, transitive_files = tool_files)
    runfiles = runfiles.merge(target[DefaultInfo].default_runfiles)
    runfiles = runfiles.merge(ctx.attr._runner[DefaultInfo].default_runfiles)
    return [DefaultInfo(executable = script, runfiles = runfiles)]
