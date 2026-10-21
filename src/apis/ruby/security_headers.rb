# frozen_string_literal: true

# Rack middleware for consistent response header hardening across Rails routes and errors.
class SecurityHeaders
  HEADERS = {
    "x-content-type-options" => "nosniff",
    "x-frame-options" => "DENY",
    "referrer-policy" => "no-referrer",
    "permissions-policy" => "camera=(), microphone=(), geolocation=()"
  }.freeze
  HSTS = "max-age=31536000"

  def initialize(app)
    @app = app
  end

  def call(env)
    status, headers, body = @app.call(env)
    HEADERS.each do |name, value|
      headers.delete_if { |key, _| key.downcase == name }
      headers[name] = value
    end
    if env["rack.url_scheme"] == "https"
      headers.delete_if { |key, _| key.downcase == "strict-transport-security" }
      headers["strict-transport-security"] = HSTS
    end
    [status, headers, body]
  end
end
