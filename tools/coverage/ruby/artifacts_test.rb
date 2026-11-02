# typed: true
# frozen_string_literal: true

require "json"
require "open3"
require "tmpdir"
require_relative "lcov"

[["1", "0", true], ["0", "0", false], ["1", "1", false]].each do |cover, fail_test, expected_success|
  Dir.mktmpdir do |directory|
    environment = {
      "TEST_UNDECLARED_OUTPUTS_DIR" => directory, "MINIMUM_LINE_COVERAGE" => "100",
      "RUBY_COVERAGE_SOURCES" => "tools/coverage/ruby/testdata/sample.rb",
      "COVER_SAMPLE" => cover, "FAIL_SAMPLE" => fail_test
    }
    _output, result = Open3.capture2e(environment, "tools/coverage/ruby/artifacts_runner.sh",
                                      "tools/coverage/ruby/testdata/sample_test.rb")
    raise "Incorrect coverage status" unless result.success? == expected_success

    report = File.read(File.join(directory, "lcov.info"))
    RubyCoverage.validate_lcov(report, ["tools/coverage/ruby/testdata/sample.rb"])
    raw = JSON.parse(File.read(File.join(directory, ".resultset.json")))
    raise "Raw SimpleCov results missing" if raw.empty?
  end
end
