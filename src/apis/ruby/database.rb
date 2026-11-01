# typed: true
# frozen_string_literal: true

require_relative "../../data/ruby/postgresql/config"

# Rails configuration supplies dependencies; an injected record keeps caller ownership.
module ApiDatabase
  def self.install(app)
    settings = app.config.x.postgresql
    path = settings.connection_file || ENV.fetch("POSTGRES_CONNECTION_FILE", nil)
    settings.record = connect(path) if settings.record.nil? && path && !path.empty?
    ActiveRecord::QueryCache.install_executor_hooks(app.executor)
    ActiveRecord::ConnectionAdapters::ConnectionPool.install_executor_hooks(app.executor)
  end

  def self.connect(path)
    record = Postgresql::Record
    record.establish_connection(Postgresql.configuration(path))
    record.connection_pool.with_connection { |connection| connection.execute("SELECT 1") }
    at_exit { record.remove_connection }
    record
  rescue StandardError
    Postgresql::Record.remove_connection
    raise
  end
end

class ApiDatabaseRailtie < Rails::Railtie
  initializer "apis.database" do |app|
    ApiDatabase.install(app)
  end
end
