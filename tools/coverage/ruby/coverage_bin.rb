# frozen_string_literal: true

require "fileutils"
require "simplecov"
require "simplecov-lcov"

# Ruby resolves require_relative through runfile symlinks. Use the real source
# root so SimpleCov does not silently discard workspace files as external.
test_files = ARGV.dup
raise ArgumentError, "At least one test script is required" if test_files.empty?

test_file = test_files.first
source_root = File.realpath(test_file).delete_suffix(test_file)
report_dir = ENV.fetch("TEST_UNDECLARED_OUTPUTS_DIR")
FileUtils.mkdir_p(report_dir)

SimpleCov::Formatter::LcovFormatter.config do |config|
  config.report_with_single_file = true
  config.single_report_path = File.join(report_dir, "lcov.info")
end
SimpleCov.formatter = SimpleCov::Formatter::LcovFormatter
SimpleCov.command_name ENV.fetch("TEST_TARGET", "ruby_tests")
SimpleCov.start do
  minimum_coverage line: Float(ENV.fetch("MINIMUM_LINE_COVERAGE"))
  root source_root
  coverage_dir report_dir
  add_filter "/external/"
  add_filter "_test.rb"
  add_filter "/tools/"
end

test_files.each { |file| require File.realpath(file) }
