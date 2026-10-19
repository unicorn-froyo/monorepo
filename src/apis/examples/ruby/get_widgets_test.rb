# frozen_string_literal: true

require_relative "get_widgets"

result = handler(event: {}, context: nil)
expected = {
  "statusCode" => 202,
  "headers" => { "Content-Type" => "application/json" },
  "body" => '""'
}
raise "Unexpected response: #{result.inspect}" unless result == expected
