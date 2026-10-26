# frozen_string_literal: true

require "fileutils"
require "simplecov"
require "simplecov-lcov"
require_relative "lcov"

# Ruby resolves require_relative through runfile symlinks. Use the real source
# root so SimpleCov does not silently discard workspace files as external.
test_files = ARGV.map { |file| File.realpath(file) }
raise "at least one Ruby test script is required" if test_files.empty?

workspace_marker = "/src/apis/"
first_source = test_files.fetch(0)
marker_index = first_source.index(workspace_marker)
raise "test is not beneath src/apis: #{first_source}" unless marker_index

source_root = first_source[0...marker_index]
report_dir = ENV.fetch("TEST_UNDECLARED_OUTPUTS_DIR")
lcov_path = File.join(report_dir, "lcov.info")
FileUtils.mkdir_p(report_dir)

class PortableLcovFormatter
  class << self
    attr_accessor :path, :root
  end

  def format(result)
    SimpleCov::Formatter::LcovFormatter.new.format(result)
    report = RubyCoverage.normalize_lcov(File.read(self.class.path), self.class.root)
    RubyCoverage.validate_lcov(report)
    File.write(self.class.path, report)
  end
end

PortableLcovFormatter.path = lcov_path
PortableLcovFormatter.root = source_root

SimpleCov::Formatter::LcovFormatter.config do |config|
  config.report_with_single_file = true
  config.single_report_path = lcov_path
end
SimpleCov.formatter = PortableLcovFormatter
SimpleCov.command_name ENV.fetch("TEST_TARGET", "ruby_tests")
SimpleCov.start do
  minimum_coverage line: Float(ENV.fetch("MINIMUM_LINE_COVERAGE"))
  root source_root
  coverage_dir report_dir
  add_filter "/external/"
  add_filter "_test.rb"
  add_filter "/tools/"
end

test_files.each { |test_file| require test_file }
