# typed: true
# frozen_string_literal: true

require "tmpdir"
require_relative "config"

settings = JSON.parse(File.read(ENV.fetch("POSTGRES_CONNECTION_FILE")))
config = Postgresql.configuration(ENV.fetch("POSTGRES_CONNECTION_FILE"))
raise "Pool must be bounded" unless config[:pool] == 5 && config[:checkout_timeout] == 5

Postgresql::Record.establish_connection(config)
Postgresql::Record.connection_pool.with_connection do |connection|
  raise "Database connection failed" unless connection.select_value("SELECT 1") == 1
end
Postgresql::Record.remove_connection

Dir.mktmpdir do |directory|
  path = File.join(directory, "connection.json")
  [{ "format_version" => 2 }, { "port" => "5432" }, { "port" => 0 }, { "port" => 65_536 },
   { "sslmode" => "prefer" }].each do |invalid|
    File.write(path, JSON.generate(settings.merge(invalid)))
    begin
      Postgresql.configuration(path)
      raise "Accepted invalid configuration"
    rescue ArgumentError
      # Invalid transport settings must fail before opening a connection.
    end
  end
end
