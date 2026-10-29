# typed: true
# frozen_string_literal: true

require_relative "../../ruby/abstract_api_base"

ENV["SECRET_KEY_BASE"] ||= "development-only-secret-key-base"

# Controller for widget resources.
class WidgetsController < AbstractApiBase
  def index
    render json: [], status: :accepted
  end
end

# Example Rails API application.
class GetWidgetsRuby < Rails::Application
  config.api_only = true
  config.eager_load = false
  config.hosts.clear
  config.secret_key_base = ENV.fetch("SECRET_KEY_BASE")
end

GetWidgetsRuby.initialize!
GetWidgetsRuby.routes.draw do
  get "/widgets", to: "widgets#index"
end

APP = GetWidgetsRuby
