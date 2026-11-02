# typed: true
# frozen_string_literal: true

# Load optional ORM APIs before Tapioca records the gem interfaces.
require "rbi"
require "active_record"
require "active_record/connection_adapters/postgresql_adapter"
require "active_support/time"
