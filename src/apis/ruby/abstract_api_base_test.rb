# frozen_string_literal: true

require "rack/mock"
require_relative "abstract_api_base"

class TestApiController < AbstractApiBase
  def message
    render json: { message: "Hello world!" }
  end
end

class TestApplication < Rails::Application
  config.api_only = true
  config.eager_load = false
  config.hosts.clear
  config.secret_key_base = "test-secret-key-base"
end

TestApplication.initialize!
TestApplication.routes.draw do
  get "/message", to: "test_api#message"
end

response = Rack::MockRequest.new(TestApplication).get("/message", "HTTP_HOST" => "localhost")
raise "Unexpected status: #{response.status}" unless response.status == 200
raise "Unexpected response: #{response.body}" unless response.body == '{"message":"Hello world!"}'
raise "Rails API mode must be enabled" unless TestApplication.config.api_only
