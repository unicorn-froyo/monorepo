# typed: true
# frozen_string_literal: true

require "json"
require "rack/mock"
require_relative "get_widgets"

response = Rack::MockRequest.new(APP).get("/widgets", "HTTP_HOST" => "localhost")
raise "Unexpected status: #{response.status}" unless response.status == (ENV["POSTGRES_CONNECTION_FILE"] ? 200 : 503)

expected = ENV["POSTGRES_CONNECTION_FILE"] ? [] : { "detail" => "Database is not configured" }
raise "Unexpected response: #{response.body}" unless JSON.parse(response.body) == expected
raise "Missing security headers" unless response["x-content-type-options"] == "nosniff"
raise "Missing security headers" unless response["x-frame-options"] == "DENY"

missing = Rack::MockRequest.new(APP).get("/missing", "HTTP_HOST" => "localhost")
raise "Unexpected status: #{missing.status}" unless missing.status == 404
raise "Missing security headers on 404" unless missing["x-content-type-options"] == "nosniff"

["/widgets", "/missing"].each do |path|
  http_response = Rack::MockRequest.new(APP).get(path, "HTTP_HOST" => "localhost")
  raise "HSTS on HTTP" if http_response["strict-transport-security"]

  https_response = Rack::MockRequest.new(APP).get(
    path, "HTTP_HOST" => "localhost", "rack.url_scheme" => "https"
  )
  raise "Missing HSTS on HTTPS for #{path}" unless https_response["strict-transport-security"] == "max-age=31536000"
end

ready = Rack::MockRequest.new(APP).get("/readyz", "HTTP_HOST" => "localhost")
raise "Readiness failed" unless ready.status == 200 && JSON.parse(ready.body) == { "ready" => true }

if ENV["POSTGRES_CONNECTION_FILE"]
  require "securerandom"
  owner = Widgets::Owner.create!(id: SecureRandom.uuid, name: "API owner")
  101.times do |index|
    Widgets::Widget.create!(id: SecureRandom.uuid, owner_id: owner.id, name: "Widget #{index}",
                            amount: "1.00000001", payload: "bytes", details: {}, created_at: Time.now.utc)
  end
  queries = []
  subscriber = ActiveSupport::Notifications.subscribe("sql.active_record") do |*args|
    payload = args.last
    queries << payload[:sql] if payload[:sql].start_with?("SELECT") && !payload[:cached]
  end
  result = Rack::MockRequest.new(APP).get("/widgets", "HTTP_HOST" => "localhost")
  ActiveSupport::Notifications.unsubscribe(subscriber)
  rows = JSON.parse(result.body)
  raise "Live query failed" unless result.status == 200 && rows.size == 101
  raise "Missing owner" unless rows.all? { |row| row["owner"] == "API owner" }
  raise "Unordered widgets" unless rows.map { |row| row["id"] } == rows.map { |row| row["id"] }.sort
  raise "N+1 queries" unless queries.size == 1
  raise "Leaked connection" if Postgresql::Record.connection_pool.active_connection?

  # Inject the model through Rails configuration, as applications and tests can.
  class FailingWidget
    def self.eager_load(*)
      raise ActiveRecord::StatementInvalid, "private database details"
    end
  end
  APP.config.x.postgresql.widget_model = FailingWidget
  failed = Rack::MockRequest.new(APP).get("/widgets", "HTTP_HOST" => "localhost")
  raise "Query failure not sanitized" unless failed.status == 500 &&
                                             JSON.parse(failed.body) == { "detail" => "Database query failed" }

  APP.config.x.postgresql.widget_model = nil
  APP.config.x.postgresql.record = nil
  unavailable = Rack::MockRequest.new(APP).get("/widgets", "HTTP_HOST" => "localhost")
  raise "Unconfigured database accepted" unless unavailable.status == 503

  APP.config.x.postgresql.record = Postgresql::Record

  Postgresql::Record.connection_pool.with_connection do |connection|
    connection.execute("SET statement_timeout = 1")
    begin
      connection.execute("SELECT pg_sleep(0.1)")
      raise "Statement timeout missing"
    rescue ActiveRecord::StatementInvalid
      connection.execute("SET statement_timeout = 10000")
    end
  end
end
