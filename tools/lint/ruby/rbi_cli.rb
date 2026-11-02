# typed: true
# frozen_string_literal: true

require_relative "rbi_generator"
RubyRbi.run(ARGV.fetch(0))
