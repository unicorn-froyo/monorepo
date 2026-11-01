# typed: true
# frozen_string_literal: true

require "minitest/autorun"
require_relative "lcov"

class RubyCoverageTest < Minitest::Test
  def test_normalizes_workspace_source_paths
    raw_report = "SF:/sandbox/workspace/src/apis/example.rb\nDA:1,1\nend_of_record\n"
    report = RubyCoverage.normalize_lcov(raw_report, "/sandbox/workspace")

    assert_equal "SF:src/apis/example.rb\nDA:1,1\nend_of_record\n", report
    RubyCoverage.validate_lcov(report)
  end

  def test_maps_resolved_sources_to_declared_bazel_paths
    report = RubyCoverage.normalize_lcov(
      "SF:/checkout/arbitrary/model.rb\nDA:1,1\nend_of_record\n", "/runfiles/_main",
      { "/checkout/arbitrary/model.rb" => "src/data/model.rb" }
    )
    assert_equal "SF:src/data/model.rb\nDA:1,1\nend_of_record\n", report
  end

  def test_rejects_empty_reports
    assert_raises(RuntimeError) { RubyCoverage.validate_lcov("TN:\n") }
  end

  def test_removes_dot_prefix
    report = RubyCoverage.normalize_lcov("SF:./src/apis/example.rb\n", "/workspace")

    assert_equal "SF:src/apis/example.rb\n", report
  end

  def test_rejects_external_sources
    assert_raises(RuntimeError) { RubyCoverage.validate_lcov("SF:external/dependency.rb\nDA:1,1\nend_of_record\n") }
  end

  def test_rejects_missing_intended_sources
    assert_raises(RuntimeError) do
      RubyCoverage.validate_lcov("SF:src/data/model.rb\nDA:1,1\nend_of_record\n", ["src/data/missing.rb"])
    end
  end

  def test_rejects_missing_or_invalid_line_coverage
    assert_raises(RuntimeError) { RubyCoverage.validate_lcov("SF:src/data/model.rb\nend_of_record\n") }
    assert_raises(RuntimeError) { RubyCoverage.validate_lcov("SF:src/data/model.rb\nDA:invalid\nend_of_record\n") }
  end

  def test_rejects_absolute_paths
    assert_raises(RuntimeError) { RubyCoverage.validate_lcov("SF:/sandbox/src/apis/example.rb\n") }
  end
end
