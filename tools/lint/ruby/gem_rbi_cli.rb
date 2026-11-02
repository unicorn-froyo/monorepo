# typed: true
# frozen_string_literal: true

require_relative "gem_rbi"
GemRbi.generate(File.expand_path(ARGV.fetch(0)))
