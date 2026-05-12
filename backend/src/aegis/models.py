"""SQLAlchemy ORM models."""
from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import (
    DateTime,
    ForeignKey,
    Integer,
    String,
    TypeDecorator,
    UniqueConstraint,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class UTCDateTime(TypeDecorator):
    """DateTime that always returns UTC-aware datetimes on read.

    SQLAlchemy's `DateTime(timezone=True)` on SQLite drops tzinfo because the
    backend stores ISO strings without a designator. This decorator re-attaches
    UTC on both write and read, ensuring the Python-side datetime is always
    tz-aware. Required so Pydantic serializes timestamps as `...+00:00`
    instead of `...` (no designator) on the wire, which iOS's
    ISO8601DateFormatter cannot parse.
    """

    impl = DateTime(timezone=True)
    cache_ok = True

    def process_bind_param(self, value, dialect):
        if value is None:
            return None
        if value.tzinfo is None:
            return value.replace(tzinfo=UTC)
        return value.astimezone(UTC)

    def process_result_value(self, value, dialect):
        if value is None:
            return None
        if value.tzinfo is None:
            return value.replace(tzinfo=UTC)
        return value


def _utcnow() -> datetime:
    return datetime.now(UTC)


class Base(DeclarativeBase):
    pass


class Device(Base):
    __tablename__ = "device"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    push_token: Mapped[str | None] = mapped_column(String, nullable=True)
    tier: Mapped[str] = mapped_column(String, default="free", nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        UTCDateTime, default=_utcnow, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        UTCDateTime,
        default=_utcnow,
        onupdate=_utcnow,
        nullable=False,
    )

    addresses: Mapped[list[WatchedAddress]] = relationship(
        back_populates="device", cascade="all, delete-orphan"
    )


class WatchedAddress(Base):
    __tablename__ = "watched_address"
    __table_args__ = (
        UniqueConstraint("device_id", "address", "chain", name="uq_watched_addr"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    device_id: Mapped[str] = mapped_column(
        ForeignKey("device.id", ondelete="CASCADE"), nullable=False
    )
    address: Mapped[str] = mapped_column(String, nullable=False)
    chain: Mapped[str] = mapped_column(String, default="ethereum", nullable=False)
    nickname: Mapped[str | None] = mapped_column(String, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        UTCDateTime, default=_utcnow, nullable=False
    )

    device: Mapped[Device] = relationship(back_populates="addresses")
    approvals: Mapped[list[Approval]] = relationship(
        back_populates="watched_address", cascade="all, delete-orphan"
    )


class Token(Base):
    __tablename__ = "token"
    __table_args__ = (UniqueConstraint("chain", "address", name="uq_token"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    chain: Mapped[str] = mapped_column(String, nullable=False)
    address: Mapped[str] = mapped_column(String, nullable=False)
    symbol: Mapped[str | None] = mapped_column(String, nullable=True)
    decimals: Mapped[int | None] = mapped_column(Integer, nullable=True)
    name: Mapped[str | None] = mapped_column(String, nullable=True)
    first_seen_at: Mapped[datetime] = mapped_column(
        UTCDateTime, default=_utcnow, nullable=False
    )


class Approval(Base):
    __tablename__ = "approval"
    __table_args__ = (
        UniqueConstraint(
            "watched_address_id", "token_id", "spender", name="uq_approval"
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    watched_address_id: Mapped[int] = mapped_column(
        ForeignKey("watched_address.id", ondelete="CASCADE"), nullable=False
    )
    token_id: Mapped[int] = mapped_column(ForeignKey("token.id"), nullable=False)
    spender: Mapped[str] = mapped_column(String, nullable=False)
    amount: Mapped[str] = mapped_column(String, nullable=False)
    block_number: Mapped[int] = mapped_column(Integer, nullable=False)
    tx_hash: Mapped[str] = mapped_column(String, nullable=False)
    first_seen_at: Mapped[datetime] = mapped_column(
        UTCDateTime, default=_utcnow, nullable=False
    )
    last_seen_at: Mapped[datetime] = mapped_column(
        UTCDateTime, default=_utcnow, onupdate=_utcnow, nullable=False
    )

    watched_address: Mapped[WatchedAddress] = relationship(back_populates="approvals")
    # no back_populates: Token intentionally has no Approval backref (week-1 YAGNI)
    token: Mapped[Token] = relationship()
