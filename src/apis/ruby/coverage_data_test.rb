# frozen_string_literal: true

# This second suite checks ordered loading and runtime data in the wrapper.
raise "The first suite did not run" unless defined?(TestApplication) && TestApplication.initialized?

fixture = File.join(
  ENV.fetch("TEST_SRCDIR"), ENV.fetch("TEST_WORKSPACE"),
  "src/apis/ruby/coverage_fixture.txt"
)
expected = ENV.fetch("COVERAGE_FIXTURE_EXPECTED", "coverage runtime data")
raise "Runtime data was not preserved" unless File.read(fixture).strip == expected
