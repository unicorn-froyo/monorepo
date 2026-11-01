# typed: true
# frozen_string_literal: true

require "net/http"
require "open3"
require "socket"
require "timeout"
require_relative "get_widgets"

module ServerTest
  include Kernel

  module_function

  def ready?(port)
    Net::HTTP.get_response(URI("http://127.0.0.1:#{port}/readyz")).code == "200"
  rescue Errno::ECONNREFUSED, EOFError
    false
  end

  def wait_for_server(port, process)
    Timeout.timeout(30) do
      loop do
        raise "Server exited during startup" unless process.alive?
        break if ready?(port)

        sleep 0.05
      end
    end
  end

  def check_live_data(port)
    Widgets::Owner.create!(id: "00000000-0000-0000-0000-000000000001", name: "Process owner")
    Widgets::Widget.create!(id: "00000000-0000-0000-0000-000000000002",
                            owner_id: "00000000-0000-0000-0000-000000000001", name: "Process widget",
                            amount: "1", payload: "x", details: {}, created_at: Time.now.utc)
    response = Net::HTTP.get_response(URI("http://127.0.0.1:#{port}/widgets"))
    rows = JSON.parse(response.body || raise("Empty HTTP response"))
    return if response.code == "200" && rows.any? { |row| row["name"] == "Process widget" }

    raise "Process did not read live PostgreSQL"
  end

  def terminate(process)
    Process.kill("TERM", process.pid)
    Timeout.timeout(15) { process.join }
    return if process.value.success? || process.value.termsig == Signal.list.fetch("TERM")

    raise "Server failed during shutdown"
  end

  def cleanup(process, reader)
    if process.alive?
      Process.kill("KILL", process.pid)
      process.join
    end
    reader.join
  end
end

listener = TCPServer.new("127.0.0.1", 0)
port = listener.addr[1]
listener.close
command = [RbConfig.ruby, "-rbundler/setup", "-e", 'load Gem.bin_path("puma", "puma")', "--",
           "-b", "tcp://127.0.0.1:#{port}", "src/apis/examples/ruby/config.ru"]
Open3.popen2e(*command) do |input, output, process|
  input.close
  reader = Thread.new { output.read }
  begin
    ServerTest.wait_for_server(port, process)
    ServerTest.check_live_data(port)
    ServerTest.terminate(process)
  ensure
    ServerTest.cleanup(process, reader)
  end
end

_output, failure = Open3.capture2e({ "POSTGRES_CONNECTION_FILE" => "/missing/private-connection.json" }, *command)
raise "Invalid connection did not fail startup" if failure.success?
