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
  def add_filter(path = nil, &block); end
  def track_files(pattern); end
end

module ActiveRecord
  class ActiveRecordError < StandardError; end
  class StatementInvalid < ActiveRecordError; end
  class ConnectionNotEstablished < ActiveRecordError; end
  class Rollback < ActiveRecordError; end

  class Base
    def self.abstract_class=(value); end
    def self.table_name=(value); end
    def self.lock_optimistically=(value); end
    def self.alias_attribute(name, column); end
    def self.has_many(name, **options); end
    def self.belongs_to(name, **options); end
    def self.establish_connection(config); end
    def self.remove_connection; end
    def self.connection_pool; end
    def self.connected?; end
    def self.create!(**attributes); end
    def self.transaction(&block); end
    def self.where(**conditions); end
    def self.count; end
    def self.one?; end
    def self.first; end
    def self.eager_load(*associations); end
  end

  module QueryCache
    def self.install_executor_hooks(executor); end
  end

  module ConnectionAdapters
    class ConnectionPool
      def self.install_executor_hooks(executor); end
    end
  end
end

module ActiveSupport
  class Logger < ::Logger; end
  module Notifications
    def self.subscribe(name, &block); end
    def self.unsubscribe(subscriber); end
  end
end

module Rails
  def self.application; end
end
