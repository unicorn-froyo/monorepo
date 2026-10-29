# typed: true
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

["/message", "/missing"].each do |path|
  result = Rack::MockRequest.new(TestApplication).get(path, "HTTP_HOST" => "localhost")
  raise "Missing nosniff on #{path}" unless result["x-content-type-options"] == "nosniff"
  raise "Missing frame protection on #{path}" unless result["x-frame-options"] == "DENY"
  raise "Missing referrer policy on #{path}" unless result["referrer-policy"] == "no-referrer"
  unless result["permissions-policy"] == "camera=(), microphone=(), geolocation=()"
    raise "Missing permissions policy on #{path}"
  end
  raise "HSTS on HTTP" if result["strict-transport-security"]
end

https_response = Rack::MockRequest.new(TestApplication).get(
  "/message", "HTTP_HOST" => "localhost", "rack.url_scheme" => "https"
)
raise "Missing HSTS on HTTPS" unless https_response["strict-transport-security"] == "max-age=31536000"
