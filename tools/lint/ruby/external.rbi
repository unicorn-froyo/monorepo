# typed: true

# Narrow interfaces for dynamic framework APIs used by this repository.
module Rails
  class Railtie
    def self.initializer(name, &block); end
  end

  class Application
    def self.config; end
    def self.initialize!; end
    def self.routes; end
  end
end

module ActionController
  class API
    def render(**options); end
  end
end

module Rack
  class MockRequest
    def initialize(app); end
    def get(path, headers = {}); end
  end
end

module Minitest
  class Test
    def assert_equal(expected, actual); end
    def assert_raises(exception, &block); end
  end
end

module SimpleCov
  module Formatter
    class LcovFormatter
      def self.config(&block); end
      def format(result); end
    end
  end

  def self.formatter=(formatter); end
  def self.command_name(name); end
  def self.start(&block); end
end

# Rails routes, Rackup, and SimpleCov evaluate these blocks with a dynamic
# receiver. Sorbet sees that receiver as the top level object.
class Object
  def get(path, to:); end
  def run(app); end
  def minimum_coverage(line:); end
  def root(path); end
  def coverage_dir(path); end
  def add_filter(path); end
end
