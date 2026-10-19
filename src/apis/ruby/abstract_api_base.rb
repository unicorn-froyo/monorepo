# frozen_string_literal: true

require "json"

# Base class for API Gateway-backed Lambda handlers.
class AbstractApiBase
  def execute(_request)
    raise NotImplementedError, "Subclasses must implement execute"
  end

  def response(message, status_code: 200, headers: nil)
    {
      "statusCode" => status_code,
      "headers" => headers || { "Content-Type" => "application/json" },
      "body" => JSON.generate(message)
    }
  end

  def self.aws_lambda_handler(*args, **kwargs)
    command = new(*args, **kwargs)
    lambda do |event:, context:| # rubocop:disable Lint/UnusedBlockArgument
      command.execute(event)
    end
  end
end
