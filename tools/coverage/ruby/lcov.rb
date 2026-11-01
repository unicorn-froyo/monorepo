# typed: true
# frozen_string_literal: true

module RubyCoverage
  module_function

  def normalize_lcov(report, source_root, logical_paths = {})
    prefix = "#{source_root}/"
    report.lines.map do |line|
      next line unless line.start_with?("SF:")

      path = File.expand_path(line.delete_prefix("SF:").strip, source_root)
      path = logical_paths.fetch(path, path.delete_prefix(prefix))
      "SF:#{path.tr('\\\\', '/')}\n"
    end.join
  end

  def validate_lcov(report, intended = [])
    sources = report.lines.grep(/^SF:/).map { |line| line.delete_prefix("SF:").strip }
    Kernel.raise "LCOV report contains no source files" if sources.empty?

    validate_portable_sources(sources)
    validate_application_sources(sources)
    validate_intended_sources(sources, intended)
    report.split("end_of_record\n").reject(&:empty?).each { |record| validate_record(record) }
  end

  def validate_intended_sources(sources, intended)
    intended.each do |source|
      Kernel.raise "LCOV report is missing #{source}" unless sources.include?(source)
    end
  end

  def validate_record(record)
    lines = record.lines.grep(/^DA:/)
    Kernel.raise "LCOV record contains no line coverage" if lines.empty?
    return if lines.all? { |line| line.match?(/^DA:[1-9][0-9]*,[0-9]+\n$/) }

    Kernel.raise "LCOV record contains invalid line coverage"
  end

  def validate_application_sources(sources)
    return if sources.any? { |path| path.start_with?("src/") || path.start_with?("tools/") }

    Kernel.raise "LCOV report contains no workspace application sources"
  end

  def validate_portable_sources(sources)
    return unless sources.any? { |path| path.start_with?("/") || path.include?("\\\\") }

    Kernel.raise "LCOV report contains a non-portable source path"
  end
end
