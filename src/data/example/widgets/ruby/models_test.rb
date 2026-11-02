# typed: true
# frozen_string_literal: true

require "securerandom"
require "bigdecimal"
require_relative "models"

Postgresql::Record.establish_connection(Postgresql.configuration(ENV.fetch("POSTGRES_CONNECTION_FILE")))
owner_id = SecureRandom.uuid
widget_id = SecureRandom.uuid
created = Time.utc(2026, 10, 29, 12, 0, 0, 123_456)
Widgets::Owner.create!(id: owner_id, name: "Ruby owner")
widget = Widgets::Widget.create!(
  id: widget_id, owner_id: owner_id, name: "Ruby widget", version: 9_007_199_254_740_993,
  amount: BigDecimal("1234567890123456789012.12345678"), payload: "\x00\xff".b,
  details: { "nested" => [1, true] }, created_at: created, optional_text: nil
)
widget.reload
loaded_owner = widget.owner
unless loaded_owner && loaded_owner.id == owner_id && loaded_owner.widgets.first!.id == widget_id
  raise "Relationship failed"
end
raise "Precision lost" unless widget.version == 9_007_199_254_740_993
raise "Decimal changed" unless widget.amount == BigDecimal("1234567890123456789012.12345678")
raise "Binary changed" unless widget.payload == "\x00\xff".b
raise "JSON changed" unless widget.details == { "nested" => [1, true] }
raise "Timestamp changed" unless widget.created_at == created
raise "NULL changed" unless widget.optional_text.nil?

Widgets::Widget.transaction do
  widget.update!(optional_text: "committed")
  Widgets::Outbox.create!(id: SecureRandom.uuid, widget_id: widget_id, event_type: "updated")
end
raise "Commit failed" unless widget.reload.optional_text == "committed" && Widgets::Outbox.one?
raise "Outbox relationship failed" unless Widgets::Outbox.first!.widget&.id == widget_id

Widgets::Widget.transaction do
  widget.update!(optional_text: "rolled back")
  Widgets::Outbox.create!(id: SecureRandom.uuid, widget_id: widget_id, event_type: "discarded")
  raise ActiveRecord::Rollback
end
raise "Rollback failed" unless widget.reload.optional_text == "committed" && Widgets::Outbox.one?

revision = widget.version
changed = Widgets::Widget.where(id: widget_id, revision: revision).update_all(revision: revision + 1)
stale = Widgets::Widget.where(id: widget_id, revision: revision).update_all(revision: revision + 1)
raise "Compare-and-swap failed" unless changed == 1 && stale.zero?

["CREATE TABLE widgets.forbidden (id integer)", "SELECT * FROM widgets.flyway_schema_history"].each do |sql|
  Postgresql::Record.connection_pool.with_connection { |connection| connection.execute(sql) }
  raise "Application role has excessive privileges"
rescue ActiveRecord::StatementInvalid
  # Flyway alone owns schema changes and migration history.
end
begin
  Widgets::Widget.where(id: widget_id).update_all(revision: 0)
  raise "Constraint was bypassed"
rescue ActiveRecord::StatementInvalid
  # Database constraints also protect bulk writes.
end
Postgresql::Record.remove_connection
