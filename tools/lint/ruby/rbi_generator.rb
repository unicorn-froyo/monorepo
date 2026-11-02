# typed: true
# frozen_string_literal: true

require "fileutils"
require "open3"
require "rbi"
require "sorbet-runtime"
require "tmpdir"

module RubyRbi
  OUTPUTS = {
    "gems" => "third_party/ruby/rbi/gems",
    "dsl" => "src/data/example/widgets/ruby/rbi"
  }.freeze
  # Sorbet already ships interfaces for these Ruby standard-library gems.
  STDLIB = %w[base64 bigdecimal drb json logger securerandom timeout tsort uri].freeze

  def self.workspace(mode)
    return ENV.fetch("BUILD_WORKSPACE_DIRECTORY") if mode == "--update"

    File.join(ENV.fetch("TEST_SRCDIR"), ENV.fetch("TEST_WORKSPACE"))
  end

  def self.run(mode)
    raise ArgumentError, "Expected --check or --update" unless %w[--check --update].include?(mode)

    Dir.mktmpdir("ruby-rbi-", ENV.fetch("TEST_TMPDIR")) do |scratch|
      generate(scratch)
      FileUtils.cp_r(scratch, File.join(ENV.fetch("TEST_UNDECLARED_OUTPUTS_DIR"), "generated"))
      OUTPUTS.each do |kind, path|
        synchronize(File.join(scratch, kind), File.join(workspace(mode), path), update: mode == "--update")
      end
    end
  end

  def self.generate(scratch)
    command = [RbConfig.ruby, File.realpath(Gem.bin_path("tapioca", "tapioca"))]
    run_command(command + gem_arguments(scratch), scratch, "gem")
    retain_core_signatures(Dir.glob("#{scratch}/gems/activesupport@*.rbi").fetch(0))
    generate_models(command, scratch)
  end

  def self.gem_arguments(scratch)
    requires = File.realpath(File.join(__dir__, "rbi_requires.rb"))
    ["gem", "activerecord", "pg", "rbi", "parser", "--include-dependencies", "--no-doc", "--no-loc",
     "--no-auto-strictness", "--typed-overrides", "activesupport:true", "--workers=1",
     "--postrequire=#{requires}", "--exclude", *STDLIB, "--outdir=#{scratch}/gems"]
  end

  # These Active Support core extensions conflict with Sorbet's embedded RBIs.
  # Keep the embedded signatures instead of disabling the entire generated RBI.
  def self.retain_core_signatures(path)
    tree = RBI::Parser.parse_file(path)
    index = tree.index
    ["::Date#to_time", "::Exception#as_json", "::Time::<self>#at"].each do |name|
      definitions = index[name]
      raise "Missing expected Active Support core extension #{name}" if definitions.empty?

      definitions.each(&:detach)
    end
    File.write(path, tree.string)
  end

  def self.generate_models(command, scratch)
    loader = File.realpath(File.join(__dir__, "rbi_models.rb"))
    command = [command.fetch(0), "-r", loader, command.fetch(1)]
    args = ["dsl", "Widgets::Owner", "Widgets::Widget", "Widgets::Outbox", "--workers=1",
            "--only", "ActiveRecordColumns", "ActiveRecordAssociations", "ActiveRecordRelations",
            "--outdir=#{scratch}/dsl"]
    run_command(command + args, scratch, "dsl")
  end

  def self.bundle_environment
    specification = Gem.loaded_specs.fetch("tapioca").loaded_from
    {
      "BUNDLE_GEMFILE" => File.realpath(ENV.fetch("BUNDLE_GEMFILE")),
      "BUNDLE_PATH" => canonical_bundle_root(ENV.fetch("BUNDLE_PATH"), specification)
    }
  end

  def self.canonical_bundle_root(bundle, specification)
    relative = Pathname.new(specification).relative_path_from(Pathname.new(bundle)).to_s
    physical = File.realpath(specification)
    raise "Unsupported installed gem layout" unless physical.end_with?("/#{relative}")

    physical.delete_suffix(relative)
  end

  def self.run_command(command, scratch, kind)
    # Canonical paths keep Tapioca source attribution consistent inside runfiles.
    environment = bundle_environment
    File.write(File.join(ENV.fetch("TEST_UNDECLARED_OUTPUTS_DIR"), "rbi-#{kind}-command.log"), command.inspect)
    output, result = T.unsafe(Open3).capture2e(environment, *command, chdir: scratch)
    File.write(File.join(ENV.fetch("TEST_UNDECLARED_OUTPUTS_DIR"), "rbi-#{kind}.log"), output)
    return if result.success?

    raise "Tapioca #{kind} failed:\n#{output.lines.first(30).join}"
  end

  def self.snapshot(directory)
    Dir.glob("**/*.rbi", base: directory).sort.to_h do |path|
      [path, File.binread(File.join(directory, path))]
    end
  end

  def self.synchronize(generated, destination, update:)
    expected = snapshot(generated)
    raise "Tapioca produced no RBIs in #{generated}" if expected.empty?

    actual = snapshot(destination)
    return write_snapshot(expected, actual, destination) if update
    return if actual == expected

    changed = (actual.keys | expected.keys).reject { |path| actual[path] == expected[path] }
    raise "Stale RBIs: #{changed.join(', ')}. Run bazelisk run --config=agent //tools/lint/ruby:rbi_update"
  end

  def self.write_snapshot(expected, actual, destination)
    (actual.keys - expected.keys).each { |path| File.delete(File.join(destination, path)) }
    expected.each do |path, content|
      target = File.join(destination, path)
      FileUtils.mkdir_p(File.dirname(target))
      File.binwrite(target, content)
    end
  end
end
