# frozen_string_literal: true

module RubyCoverage
  module_function

  def normalize_lcov(report, source_root)
    prefix = "#{source_root}/"
    report.lines.map do |line|
      next line unless line.start_with?("SF:")

      path = line.delete_prefix("SF:").strip
      path = path.delete_prefix(prefix)
      path = path.delete_prefix("./")
      "SF:#{path.tr('\\\\', '/')}\n"
    end.join
  end

  def validate_lcov(report)
    sources = report.lines.grep(/^SF:/).map { |line| line.delete_prefix("SF:").strip }
    raise "LCOV report contains no source files" if sources.empty?

    validate_application_sources(sources)
    validate_portable_sources(sources)
  end

  def validate_application_sources(sources)
    return if sources.any? { |path| path.start_with?("src/apis/") }

    raise "LCOV report contains no src/apis application sources"
  end

  def validate_portable_sources(sources)
    return unless sources.any? { |path| path.start_with?("/") || path.include?("\\\\") }

    raise "LCOV report contains a non-portable source path"
  end
end
