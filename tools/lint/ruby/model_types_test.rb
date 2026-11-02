# typed: true
# frozen_string_literal: true

require "open3"
require "sorbet-runtime"
require "tmpdir"

root = File.join(ENV.fetch("TEST_SRCDIR"), ENV.fetch("TEST_WORKSPACE"))
interfaces = Dir.glob("third_party/ruby/rbi/gems/*.rbi", base: root) + ["src/data/example/widgets/ruby/models.rbi"]
sources = %w[tools/lint/ruby/external.rbi src/data/ruby/postgresql/config.rb
             src/data/example/widgets/ruby/models.rb]
command = [RbConfig.ruby, Gem.bin_path("sorbet", "srb"), "tc", "--no-config", "--typed=true", *interfaces, *sources]
valid = "tools/lint/ruby/testdata/model_types.rb"
# Sorbet cannot resolve Open3 overloads with a dynamically sized argv.
output, result = T.unsafe(Open3).capture2e(*(command + [valid]), chdir: root)
raise "Generated model types are invalid:\n#{output}" unless result.success?

Dir.mktmpdir do |directory|
  source = File.read(File.join(root, valid))
  invalid = source.sub("    T.assert_type!(widget.id, String)", <<~RUBY)
    widget.version = "wrong"
    widget.amount = "wrong"
    widget.owner = "wrong"
    widget.optional_text = 123
  RUBY
  path = File.join(directory, "invalid.rb")
  File.write(path, invalid)
  diagnostics, status = T.unsafe(Open3).capture2e(*(command + [path]), chdir: root)
  raise "Incorrect model types passed Sorbet" if status.success?

  %w[widget.version widget.amount widget.owner widget.optional_text].each do |assignment|
    line = invalid.lines.index { |text| text.include?("#{assignment} =") }
    raise "Missing invalid assignment" if line.nil?

    unless diagnostics.include?("#{path}:#{line + 1}:") && diagnostics.include?("7002")
      raise "Missing typed model error for #{assignment}:\n#{diagnostics}"
    end
  end
end
