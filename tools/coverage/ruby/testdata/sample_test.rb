# typed: true
# frozen_string_literal: true

require_relative "sample"
CoverageSample.value if ENV["COVER_SAMPLE"] == "1"
raise "deliberate failure" if ENV["FAIL_SAMPLE"] == "1"
