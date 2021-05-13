"""index.bzl provides the bzl_lint_test rule"""

load("@bazel_skylib//lib:shell.bzl", "shell")

def _check_file(f):
    base = f.basename
    return base in ("WORKSPACE", "BUILD", "BUILD.bazel") or base.endswith(".bzl")

def _bzl_lint_test_impl(ctx):
    files = [f for f in ctx.files.data if _check_file(f)]

    script = ctx.actions.declare_file(ctx.label.name + ".sh")
    content = """#!/usr/bin/env bash
set -uo pipefail
files=(
    {files}
)
buildifier={buildifier}
# warnings is the default list of warnings with exclusions:
#   bzl-visibility: we reference symbols in //go/private outside of //go.
#   confusing-name: a good font makes these very clear.
#   function-docstring: too verbose. Many functions don't need docs.
#   function-docstring-header: too verbose for now.
#   function-docstring-args: too verbose.
#   function-docstring-return: too verbose.
#   module-docstring: doesn't seem useful for many private modules.
#   name-conventions: we have non-compliant providers. We might change them
#       eventually, but we'll need to keep the old symbols for compatibility.
#   print: used for warnings.
warnings=attr-cfg,attr-license,attr-non-empty,attr-output-default,attr-single-file,build-args-kwargs,constant-glob,ctx-actions,ctx-args,depset-iteration,depset-union,dict-concatenation,duplicated-name,filetype,git-repository,http-archive,integer-division,keyword-positional-params,load,load-on-top,native-android,native-build,native-cc,native-java,native-package,native-proto,native-py,no-effect,output-group,overly-nested-depset,package-name,package-on-top,positional-args,redefined-variable,repository-name,return-value,rule-impl-return,same-origin-load,string-iteration,uninitialized,unreachable,unused-variable
ok=0
for file in "${{files[@]}}"; do
    "$buildifier" -mode=check -lint=warn -warnings="$warnings" "$file"
    if [ $? -ne 0 ]; then
        ok=1
    fi
done
exit $ok
""".format(
        buildifier = shell.quote(ctx.executable._buildifier.short_path),
        files = "\n".join([shell.quote(f.path) for f in files]),
    )
    ctx.actions.write(script, content, is_executable = True)

    return [DefaultInfo(
        executable = script,
        default_runfiles = ctx.runfiles(
            files = [script, ctx.executable._buildifier] + files,
        ),
    )]

bzl_lint_test = rule(
    implementation = _bzl_lint_test_impl,
    attrs = {
        "data": attr.label_list(
            allow_files = True,
        ),
        "_buildifier": attr.label(
            default = "@com_github_bazelbuild_buildtools//buildifier",
            executable = True,
            cfg = "exec",
        ),
    },
    test = True,
)
