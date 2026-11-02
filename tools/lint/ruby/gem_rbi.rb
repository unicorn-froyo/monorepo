# typed: true
# frozen_string_literal: true

require "fileutils"
require "open3"
require "rbi"
require "sorbet-runtime"
require "tmpdir"

module GemRbi
  # Sorbet supplies these standard-library interfaces.
  STDLIB = %w[base64 bigdecimal drb json logger securerandom timeout tsort uri].freeze

  def self.generate(destination)
    FileUtils.mkdir_p(destination)
    Dir.mktmpdir("scratch-", destination) do |scratch|
      command = [RbConfig.ruby, File.realpath(Gem.bin_path("tapioca", "tapioca"))]
      run_command(command + gem_arguments(scratch), scratch, "gem")
      retain_core_signatures(Dir.glob("#{scratch}/gems/activesupport@*.rbi").fetch(0))
      FileUtils.cp_r("#{scratch}/gems/.", destination)
    end
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
    File.write(File.join(ENV.fetch("TEST_UNDECLARED_OUTPUTS_DIR", scratch), "rbi-#{kind}-command.log"), command.inspect)
    output, result = T.unsafe(Open3).capture2e(environment, *command, chdir: scratch)
    File.write(File.join(ENV.fetch("TEST_UNDECLARED_OUTPUTS_DIR", scratch), "rbi-#{kind}.log"), output)
    return if result.success?

    raise "Tapioca #{kind} failed:\n#{output.lines.first(30).join}"
  end
end
