# typed: true
# frozen_string_literal: true

require "json"
require "active_record"

module Postgresql
  # All application models share this pool; callers may inject another abstract base.
  class Record < ActiveRecord::Base
    self.abstract_class = true
  end

  def self.configuration(path)
    settings = JSON.parse(File.read(path))
    validate(settings)
    connection_options(settings)
  end

  def self.validate(settings)
    raise ArgumentError, "Unsupported PostgreSQL connection format" unless settings.fetch("format_version") == 1

    port = settings.fetch("port")
    raise ArgumentError, "Invalid PostgreSQL port" unless port.is_a?(Integer) && (1..65_535).cover?(port)
    return if %w[disable require verify-ca verify-full].include?(settings.fetch("sslmode"))

    raise ArgumentError, "Unsupported PostgreSQL TLS policy"
  end

  def self.connection_options(settings)
    {
      adapter: "postgresql", host: settings.fetch("host"), port: settings.fetch("port"),
      database: settings.fetch("database"), username: settings.fetch("user"),
      password: settings.fetch("password"), sslmode: settings.fetch("sslmode"),
      pool: 5, checkout_timeout: 5, connect_timeout: 5,
      variables: { statement_timeout: 10_000 }, database_tasks: false
    }
  end
end
