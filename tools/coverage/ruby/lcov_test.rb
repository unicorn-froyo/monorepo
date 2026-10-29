# typed: true
# frozen_string_literal: true

require "minitest/autorun"
require_relative "lcov"

class RubyCoverageTest < Minitest::Test
  def test_normalizes_workspace_source_paths
    raw_report = "SF:/sandbox/workspace/src/apis/example.rb\nend_of_record\n"
    report = RubyCoverage.normalize_lcov(raw_report, "/sandbox/workspace")

    assert_equal "SF:src/apis/example.rb\nend_of_record\n", report
    RubyCoverage.validate_lcov(report)
  end

  def test_rejects_empty_reports
    assert_raises(RuntimeError) { RubyCoverage.validate_lcov("TN:\n") }
  end

  def test_removes_dot_prefix
    report = RubyCoverage.normalize_lcov("SF:./src/apis/example.rb\n", "/workspace")

    assert_equal "SF:src/apis/example.rb\n", report
  end

  def test_rejects_absolute_paths
    assert_raises(RuntimeError) { RubyCoverage.validate_lcov("SF:/sandbox/src/apis/example.rb\n") }
  end
end
