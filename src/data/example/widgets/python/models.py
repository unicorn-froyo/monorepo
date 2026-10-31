"""SQLAlchemy mappings for the Flyway-owned example schema."""

from datetime import datetime
from decimal import Decimal
from uuid import UUID

from sqlalchemy import BigInteger, DateTime, ForeignKey, Numeric
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    """Example entity registry; never call metadata.create_all for migrations."""


class Owner(Base):
    __tablename__ = "owners"
    __table_args__ = {"schema": "widgets"}

    id: Mapped[UUID] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column("display_name")
    widgets: Mapped[list["Widget"]] = relationship(back_populates="owner")


class Widget(Base):
    __tablename__ = "widgets"
    __table_args__ = {"schema": "widgets"}

    id: Mapped[UUID] = mapped_column(primary_key=True)
    owner_id: Mapped[UUID] = mapped_column(ForeignKey("widgets.owners.id"))
    name: Mapped[str] = mapped_column("display_name")
    version: Mapped[int] = mapped_column("revision", BigInteger)
    amount: Mapped[Decimal] = mapped_column(Numeric(30, 8))
    payload: Mapped[bytes]
    details: Mapped[dict] = mapped_column("metadata", JSONB)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    optional_text: Mapped[str | None]
    owner: Mapped[Owner] = relationship(back_populates="widgets")


class Outbox(Base):
    __tablename__ = "outbox"
    __table_args__ = {"schema": "widgets"}

    id: Mapped[UUID] = mapped_column(primary_key=True)
    widget_id: Mapped[UUID] = mapped_column(ForeignKey("widgets.widgets.id"))
    event_type: Mapped[str]
