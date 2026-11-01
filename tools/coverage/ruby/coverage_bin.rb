# typed: true
# frozen_string_literal: true

require "fileutils"
require "simplecov"
require "simplecov-lcov"

# Ruby resolves runfile symlinks; retain the declared paths for portable LCOV.
test_files = ARGV.map { |file| File.realpath(file) }
raise "at least one Ruby test script is required" if test_files.empty?

source_root = File.join(ENV.fetch("TEST_SRCDIR"), ENV.fetch("TEST_WORKSPACE"))
source_files = ENV.fetch("RUBY_COVERAGE_SOURCES").split(":")
raise "at least one intended Ruby source is required" if source_files.empty?

measured_sources = source_files.map { |file| File.realpath(File.join(source_root, file)) }
coverage_root = File.dirname(measured_sources.fetch(0))
until measured_sources.all? { |file| file.start_with?(File.join(coverage_root, "")) }
  coverage_root = File.dirname(coverage_root)
end
report_dir = ENV.fetch("TEST_UNDECLARED_OUTPUTS_DIR")
lcov_path = File.join(report_dir, "lcov.info")
FileUtils.mkdir_p(report_dir)

class PortableLcovFormatter
  class << self
    attr_accessor :path, :root, :sources, :logical_paths
  end

  def format(result)
    SimpleCov::Formatter::LcovFormatter.new.format(result)
    report = RubyCoverage.normalize_lcov(File.read(self.class.path), self.class.root, self.class.logical_paths)
    RubyCoverage.validate_lcov(report, self.class.sources)
    File.write(self.class.path, report)
  end
end

PortableLcovFormatter.path = lcov_path
PortableLcovFormatter.root = coverage_root
PortableLcovFormatter.sources = source_files
PortableLcovFormatter.logical_paths = measured_sources.zip(source_files).to_h

SimpleCov::Formatter::LcovFormatter.config do |config|
  config.report_with_single_file = true
  config.single_report_path = lcov_path
end
SimpleCov.formatter = PortableLcovFormatter
SimpleCov.command_name ENV.fetch("TEST_TARGET", "ruby_tests")
SimpleCov.start do
  minimum_coverage line: Float(ENV.fetch("MINIMUM_LINE_COVERAGE"))
  root coverage_root
  coverage_dir report_dir
  add_filter "/external/"
  add_filter "_test.rb"
  track_files "{#{measured_sources.join(',')}}"
  add_filter { |source| !measured_sources.include?(source.filename) }
end

require_relative "lcov"
test_files.each { |test_file| require test_file }
