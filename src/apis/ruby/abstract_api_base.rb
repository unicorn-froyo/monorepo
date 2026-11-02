# typed: true
# frozen_string_literal: true

require "action_controller/railtie"
require_relative "security_headers"
require_relative "database"

# Install response hardening before Rails handles requests or generates errors.
class ApiSecurityHeadersRailtie < Rails::Railtie
  initializer "apis.security_headers" do |app|
    app.middleware.insert_before 0, SecurityHeaders
  end
end

# Base controller for JSON APIs implemented with Rails.
class AbstractApiBase < ActionController::API
  def database_record
    Rails.application.config.x.postgresql.record
  end

  def ready
    database_record&.connection_pool&.with_connection { |connection| connection.execute("SELECT 1") }
    render json: { ready: true }
  rescue ActiveRecord::ActiveRecordError
    render json: { ready: false }, status: :service_unavailable
  end
end
