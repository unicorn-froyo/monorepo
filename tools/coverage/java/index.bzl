"""Java coverage tests using Bazel's JaCoCo instrumentation."""

load("@rules_java//java:defs.bzl", "JavaInfo")
load("//tools/coverage:config.bzl", "MINIMUM_LINE_COVERAGE")

def _java_coverage_test(ctx):
    target = ctx.attr.target
    executable = target[DefaultInfo].files_to_run.executable
    jars = []
    for source_target in ctx.attr.source_targets:
        jars.extend(source_target[JavaInfo].runtime_output_jars)
    args = [
        executable.short_path,
        str(MINIMUM_LINE_COVERAGE),
        ctx.file._agent.short_path,
        ctx.executable._jacoco.short_path,
        json.encode([f.short_path for f in jars]),
        json.encode([f.short_path for f in ctx.files.srcs]),
    ]
    script = ctx.actions.declare_file(ctx.label.name + ".sh")
    ctx.actions.write(
        script,
        "#!/bin/sh\nset -eu\nexec '%s' '%s'\n" % (
            ctx.executable._runner.short_path,
            "' '".join([arg.replace("'", "'\\''") for arg in args]),
        ),
        is_executable = True,
    )
    runfiles = ctx.runfiles(files = [executable, ctx.file._agent] + jars + ctx.files.srcs)
    for dep in [target, ctx.attr._runner, ctx.attr._jacoco]:
        runfiles = runfiles.merge(dep[DefaultInfo].default_runfiles)
    return [DefaultInfo(executable = script, runfiles = runfiles)]

java_coverage_test = rule(
    implementation = _java_coverage_test,
    attrs = {
        "srcs": attr.label_list(allow_files = [".java"], mandatory = True),
        "source_targets": attr.label_list(mandatory = True, providers = [JavaInfo]),
        "target": attr.label(executable = True, cfg = "target", mandatory = True, providers = [JavaInfo]),
        "_agent": attr.label(default = "@maven//:org_jacoco_org_jacoco_agent_runtime", allow_single_file = True),
        "_jacoco": attr.label(default = "//tools/coverage/java:jacoco", executable = True, cfg = "target"),
        "_runner": attr.label(default = "//tools/coverage/java:coverage_bin", executable = True, cfg = "target"),
    },
    test = True,
)
