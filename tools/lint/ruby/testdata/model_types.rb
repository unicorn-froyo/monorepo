# typed: true
# frozen_string_literal: true

class ModelTypes
  extend T::Sig

  sig { params(widget: Widgets::Widget).void }
  def self.check(widget)
    T.assert_type!(widget.id, String)
    T.assert_type!(widget.version, Integer)
    T.assert_type!(widget.amount, BigDecimal)
    T.assert_type!(widget.payload, String)
    T.assert_type!(widget.optional_text, T.nilable(String))
  end

  sig { params(widget: Widgets::Widget, owner: Widgets::Owner).void }
  def self.relations(widget, owner)
    T.assert_type!(widget.owner, T.nilable(Widgets::Owner))
    T.let(owner.widgets.first, T.nilable(Widgets::Widget))
    T.let(Widgets::Widget.where(owner_id: owner.id).first, T.nilable(Widgets::Widget))
  end
end
