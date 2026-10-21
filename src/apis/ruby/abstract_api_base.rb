# frozen_string_literal: true

require "action_controller/railtie"
require_relative "security_headers"

# Install response hardening before Rails handles requests or generates errors.
class ApiSecurityHeadersRailtie < Rails::Railtie
  initializer "apis.security_headers" do |app|
    app.middleware.insert_before 0, SecurityHeaders
  end
end

# Base controller for JSON APIs implemented with Rails.
class AbstractApiBase < ActionController::API
end
