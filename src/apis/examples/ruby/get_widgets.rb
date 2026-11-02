# typed: true
# frozen_string_literal: true

require_relative "../../ruby/abstract_api_base"

require_relative "../../../data/example/widgets/ruby/models"

ENV["SECRET_KEY_BASE"] ||= "development-only-secret-key-base"

# Controller for widget resources.
class WidgetsController < AbstractApiBase
  def index
    unless database_record
      render json: { detail: "Database is not configured" }, status: :service_unavailable
      return
    end

    records = widget_model.eager_load(:owner).order(:id)
    render json: records.map { |widget| { id: widget.id, name: widget.name, owner: widget.owner.name } }
  rescue ActiveRecord::ActiveRecordError
    render json: { detail: "Database query failed" }, status: :internal_server_error
  end

  def widget_model
    Rails.application.config.x.postgresql.widget_model || Widgets::Widget
  end
end

# Example Rails API application.
class GetWidgetsRuby < Rails::Application
  config.logger = ActiveSupport::Logger.new($stdout)
  config.api_only = true
  config.eager_load = false
  config.hosts.clear
  config.secret_key_base = ENV.fetch("SECRET_KEY_BASE")
end

GetWidgetsRuby.initialize!
GetWidgetsRuby.routes.draw do
  get "/widgets", to: "widgets#index"
  get "/readyz", to: "widgets#ready"
end

APP = GetWidgetsRuby
