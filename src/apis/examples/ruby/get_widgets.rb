# frozen_string_literal: true

require_relative "../../ruby/abstract_api_base"

# Example Ruby API implementation.
class GetWidgetsRuby < AbstractApiBase
  def execute(_request)
    response("", status_code: 202)
  end
end

def handler(event:, context:)
  GetWidgetsRuby.aws_lambda_handler.call(event: event, context: context)
end
