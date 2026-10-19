# frozen_string_literal: true

require_relative "abstract_api_base"

begin
  AbstractApiBase.new.execute({})
  raise "AbstractApiBase#execute should raise NotImplementedError"
rescue NotImplementedError
  # Expected.
end

class TestApi < AbstractApiBase
  def execute(request)
    response({ "request" => request })
  end
end

result = TestApi.aws_lambda_handler.call(event: "hello", context: nil)
expected = {
  "statusCode" => 200,
  "headers" => { "Content-Type" => "application/json" },
  "body" => '{"request":"hello"}'
}
raise "Unexpected response: #{result.inspect}" unless result == expected
