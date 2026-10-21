# frozen_string_literal: true

require "json"
require "rack/mock"
require_relative "get_widgets"

response = Rack::MockRequest.new(APP).get("/widgets", "HTTP_HOST" => "localhost")
raise "Unexpected status: #{response.status}" unless response.status == 202
raise "Unexpected response: #{response.body}" unless JSON.parse(response.body) == []
raise "Missing security headers" unless response["x-content-type-options"] == "nosniff"
raise "Missing security headers" unless response["x-frame-options"] == "DENY"

missing = Rack::MockRequest.new(APP).get("/missing", "HTTP_HOST" => "localhost")
raise "Unexpected status: #{missing.status}" unless missing.status == 404
raise "Missing security headers on 404" unless missing["x-content-type-options"] == "nosniff"
