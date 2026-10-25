"""Explicit dependency maintenance and offline manifest/lock consistency tests."""

load("@bazel_skylib//lib:shell.bzl", "shell")

_GO = "@io_bazel_rules_go//go:toolchain"
_RUBY = "@rules_ruby//ruby:toolchain_type"
_RUST = "@rules_rust//rust:toolchain_type"
_YQ = "@yq.bzl//yq/toolchain:type"

def _dependencies_impl(ctx):
    language = ctx.attr.language
    config = {
        "language": language,
        "mode": ctx.attr.mode,
        "inputs": [f.short_path for f in ctx.files.srcs],
        "tools": {},
        "env": {},
    }
    files = list(ctx.files.srcs)
    transitive = []
    if language == "golang":
        sdk = ctx.toolchains[_GO].sdk
        config["tools"]["go"] = sdk.go.short_path
        config["tools"]["goroot"] = sdk.root_file.short_path
        files += [sdk.go, sdk.root_file]
        transitive += [sdk.libs, sdk.headers, sdk.srcs, sdk.tools]
    elif language == "ruby":
        toolchain = ctx.toolchains[_RUBY]
        config["tools"]["ruby"] = toolchain.ruby.short_path
        config["env"] = toolchain.env
        files += toolchain.files
        if ctx.attr.mode != "test":
            bundler = [f for f in ctx.files._bundler if f.is_directory][0]
            config["tools"]["bundler"] = bundler.short_path
            files += ctx.files._bundler
    elif language == "rust" and ctx.attr.mode != "test":
        toolchain = ctx.toolchains[_RUST]
        config["tools"]["cargo"] = toolchain.cargo.short_path
        config["tools"]["rustc"] = toolchain.rustc.short_path
        transitive.append(toolchain.all_files)
    elif language == "npm":
        yq = ctx.toolchains[_YQ].yqinfo.bin
        config["tools"]["yq"] = yq.short_path
        files.append(yq)
        if ctx.attr.mode != "test":
            config["tools"]["pnpm"] = ctx.executable._pnpm.short_path

    config_file = ctx.actions.declare_file(ctx.label.name + ".json")
    ctx.actions.write(config_file, json.encode(config))
    script = ctx.actions.declare_file(ctx.label.name + ".sh")
    ctx.actions.write(
        script,
        "#!/bin/sh\nset -eu\nexec %s %s\n" % (
            shell.quote(ctx.executable._runner.short_path),
            shell.quote(config_file.short_path),
        ),
        is_executable = True,
    )
    runfiles = ctx.runfiles(files = files + [config_file], transitive_files = depset(transitive = transitive))
    runfiles = runfiles.merge(ctx.attr._runner[DefaultInfo].default_runfiles)
    if language == "npm" and ctx.attr.mode != "test":
        runfiles = runfiles.merge(ctx.attr._pnpm[DefaultInfo].default_runfiles)
    return [DefaultInfo(executable = script, runfiles = runfiles)]

def _dependency_rule(language, test = False):
    toolchains = {
        "golang": [_GO],
        "npm": [_YQ],
        "ruby": [_RUBY],
        "rust": [] if test else [_RUST],
    }[language]
    attrs = {
        "language": attr.string(default = language),
        "mode": attr.string(default = "test" if test else "check"),
        "srcs": attr.label_list(allow_files = True),
        "_runner": attr.label(default = "//tools/dependencies:runner", executable = True, cfg = "exec"),
    }
    if not test and language == "npm":
        attrs["_pnpm"] = attr.label(default = "@pnpm//:pnpm", executable = True, cfg = "exec")
    if not test and language == "ruby":
        attrs["_bundler"] = attr.label(default = "@bundle//:bundler-2.6.9", cfg = "exec")
    return rule(
        implementation = _dependencies_impl,
        attrs = attrs,
        toolchains = toolchains,
        executable = not test,
        test = test,
    )

_go_maintenance = _dependency_rule("golang")
_go_consistency_test = _dependency_rule("golang", test = True)
_npm_maintenance = _dependency_rule("npm")
_npm_consistency_test = _dependency_rule("npm", test = True)
_ruby_maintenance = _dependency_rule("ruby")
_ruby_consistency_test = _dependency_rule("ruby", test = True)
_rust_maintenance = _dependency_rule("rust")
_rust_consistency_test = _dependency_rule("rust", test = True)

def dependency_workflow(name, language, srcs):
    """Create offline .test, non-mutating networked .check, and explicit .update."""
    maintenance, consistency_test = {
        "golang": (_go_maintenance, _go_consistency_test),
        "npm": (_npm_maintenance, _npm_consistency_test),
        "ruby": (_ruby_maintenance, _ruby_consistency_test),
        "rust": (_rust_maintenance, _rust_consistency_test),
    }[language]
    consistency_test(name = name + ".test", srcs = srcs)
    for mode in ["check", "update"]:
        maintenance(name = name + "." + mode, mode = mode, srcs = srcs, tags = ["manual"])
