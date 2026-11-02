# typed: true
# frozen_string_literal: true

require "minitest/autorun"
require_relative "rbi_generator"
require_relative "rbi_requires"
require_relative "rbi_models"

class RubyRbiTest < Minitest::Test
  def test_model_interface_matches_the_migrated_schema
    arguments = ARGV.dup
    ARGV.replace(["--check"])
    load File.join(__dir__, "rbi_cli.rb")
  ensure
    ARGV.replace(arguments)
  end

  def test_dependency_interfaces_match_the_bazel_build_output
    arguments = ARGV.dup
    Dir.mktmpdir do |directory|
      ARGV.replace([directory])
      load File.join(__dir__, "gem_rbi_cli.rb")
      assert_same_interfaces(RubyRbi.snapshot(ENV.fetch("GEM_RBI_DIR")), RubyRbi.snapshot(directory))
    end
  ensure
    ARGV.replace(arguments)
  end

  def assert_same_interfaces(expected, actual)
    changed = (expected.keys | actual.keys).reject { |path| expected[path] == actual[path] }
    assert_equal [], changed
  end

  def test_core_extension_compatibility_fails_if_upstream_changes
    Dir.mktmpdir do |directory|
      path = File.join(directory, "empty.rbi")
      File.write(path, "# typed: true\n")
      assert_raises(RuntimeError) { GemRbi.retain_core_signatures(path) }
    end
  end

  def test_rejects_inconsistent_installed_gem_layout
    Dir.mktmpdir do |directory|
      specification = File.join(directory, "tapioca.gemspec")
      File.write(specification, "")
      assert_raises(RuntimeError) { GemRbi.canonical_bundle_root(File.join(directory, "unrelated"), specification) }
    end
  end

  def test_rejects_invalid_modes
    assert_raises(ArgumentError) { RubyRbi.run("--invalid") }
  end

  def test_update_uses_bazel_workspace_directory
    previous = ENV.fetch("BUILD_WORKSPACE_DIRECTORY", nil)
    ENV["BUILD_WORKSPACE_DIRECTORY"] = "/workspace"
    assert_equal "/workspace", RubyRbi.workspace("--update")
  ensure
    ENV["BUILD_WORKSPACE_DIRECTORY"] = previous
  end

  def test_generation_failure_is_reported
    Dir.mktmpdir do |directory|
      assert_raises(RuntimeError) do
        GemRbi.run_command([RbConfig.ruby, "-e", "abort 'intentional generation failure'"], directory, "failure")
      end
    end
  end

  def test_synchronization_detects_changes_and_removes_stale_files
    Dir.mktmpdir do |directory|
      source = File.join(directory, "source")
      target = File.join(directory, "target")
      FileUtils.mkdir_p(source)
      FileUtils.mkdir_p(target)
      check_synchronization(source, target)
    end
  end

  def check_synchronization(source, target)
    assert_raises(RuntimeError) { RubyRbi.synchronize(source, target, update: false) }
    File.write(File.join(source, "model.rbi"), "# typed: true\nclass Fresh; end\n")
    File.write(File.join(target, "stale.rbi"), "# typed: true\nclass Stale; end\n")
    assert_raises(RuntimeError) { RubyRbi.synchronize(source, target, update: false) }
    RubyRbi.synchronize(source, target, update: true)
    assert_equal RubyRbi.snapshot(source), RubyRbi.snapshot(target)
    RubyRbi.synchronize(source, target, update: false)
    File.write(File.join(target, "model.rbi"), "# typed: true\nclass Changed; end\n")
    assert_raises(RuntimeError) { RubyRbi.synchronize(source, target, update: false) }
  end
end
