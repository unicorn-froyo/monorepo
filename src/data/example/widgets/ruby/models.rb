# typed: true
# frozen_string_literal: true

require_relative "../../../ruby/postgresql/config"

module Widgets
  class Owner < Postgresql::Record
    self.table_name = "widgets.owners"
    alias_attribute :name, :display_name
    has_many :widgets, class_name: "Widgets::Widget", inverse_of: :owner
  end

  class Widget < Postgresql::Record
    self.table_name = "widgets.widgets"
    # Revisions are updated explicitly by compare-and-swap operations.
    self.lock_optimistically = false
    alias_attribute :name, :display_name
    alias_attribute :version, :revision
    alias_attribute :details, :metadata
    belongs_to :owner, class_name: "Widgets::Owner", inverse_of: :widgets, optional: false
  end

  class Outbox < Postgresql::Record
    self.table_name = "widgets.outbox"
    belongs_to :widget, class_name: "Widgets::Widget", optional: false
  end
end
