"""Persistence model. Business authorization and transitions belong in services."""

from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import (
    BigInteger,
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    ForeignKeyConstraint,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, CreatedAt, UUIDPrimaryKey


class User(UUIDPrimaryKey, CreatedAt, Base):
    __tablename__ = "users"
    __table_args__ = (
        CheckConstraint("role IN ('auctioneer', 'bidder')", name="valid_role"),
        CheckConstraint(
            "email = lower(btrim(email)) AND length(email) > 0", name="normalized_email"
        ),
        CheckConstraint("length(btrim(name)) > 0", name="nonempty_name"),
    )
    public_id: Mapped[UUID] = mapped_column(
        unique=True, default=uuid4, server_default=text("gen_random_uuid()")
    )
    name: Mapped[str] = mapped_column(String(150))
    email: Mapped[str] = mapped_column(String(320), unique=True)
    password_hash: Mapped[str] = mapped_column(Text)
    role: Mapped[str] = mapped_column(String(20))
    active: Mapped[bool] = mapped_column(Boolean, server_default=text("true"))


class Wallet(UUIDPrimaryKey, Base):
    __tablename__ = "wallets"
    __table_args__ = (
        CheckConstraint("balance_cents >= 0", name="nonnegative_balance"),
        CheckConstraint(
            "reserved_cents >= 0 AND reserved_cents <= balance_cents",
            name="valid_reserved_balance",
        ),
    )
    user_id: Mapped[UUID] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"), unique=True
    )
    balance_cents: Mapped[int] = mapped_column(BigInteger, server_default="0")
    reserved_cents: Mapped[int] = mapped_column(BigInteger, server_default="0")

    @property
    def available_cents(self) -> int:
        return self.balance_cents - self.reserved_cents


class Lot(UUIDPrimaryKey, CreatedAt, Base):
    __tablename__ = "lots"
    __table_args__ = (
        CheckConstraint(
            "opening_bid_cents > 0 AND min_increment_cents > 0", name="positive_prices"
        ),
        CheckConstraint(
            "starts_at < original_ends_at AND ends_at >= original_ends_at",
            name="valid_period",
        ),
        CheckConstraint(
            "status IN ('scheduled', 'live', 'closed', 'cancelled')",
            name="valid_status",
        ),
        CheckConstraint("version >= 0", name="nonnegative_version"),
        CheckConstraint(
            "(status = 'closed') = (closed_at IS NOT NULL)", name="closed_timestamp"
        ),
        ForeignKeyConstraint(
            ["id", "current_bid_id"],
            ["bids.lot_id", "bids.id"],
            name="fk_lots_current_bid_same_lot",
            use_alter=True,
            ondelete="RESTRICT",
        ),
        Index("ix_lots_status_ends_at", "status", "ends_at"),
        Index("ix_lots_seller_created_at", "seller_id", "created_at"),
    )
    seller_id: Mapped[UUID] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"))
    source_provider: Mapped[str] = mapped_column(String(80))
    external_item_id: Mapped[str] = mapped_column(String(255))
    source_url: Mapped[str] = mapped_column(Text)
    item_title: Mapped[str] = mapped_column(String(300))
    item_attributes: Mapped[dict] = mapped_column(
        JSONB, server_default=text("'{}'::jsonb")
    )
    local_image_key: Mapped[str] = mapped_column(Text)
    opening_bid_cents: Mapped[int] = mapped_column(BigInteger)
    min_increment_cents: Mapped[int] = mapped_column(BigInteger)
    starts_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    original_ends_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    ends_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    status: Mapped[str] = mapped_column(String(20), server_default="scheduled")
    current_bid_id: Mapped[UUID | None] = mapped_column()
    version: Mapped[int] = mapped_column(BigInteger, server_default="0")
    closed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class Bid(UUIDPrimaryKey, Base):
    __tablename__ = "bids"
    __table_args__ = (
        UniqueConstraint("lot_id", "sequence", name="uq_bids_lot_sequence"),
        UniqueConstraint("lot_id", "id", name="uq_bids_lot_id"),
        CheckConstraint("amount_cents > 0 AND sequence > 0", name="positive_bid"),
        CheckConstraint("key_version > 0", name="positive_key_version"),
        CheckConstraint(
            "previous_hash ~ '^[0-9a-f]{64}$' "
            "AND record_hash ~ '^[0-9a-f]{64}$' "
            "AND signature ~ '^[0-9a-f]{64}$'",
            name="valid_hashes",
        ),
        Index("ix_bids_bidder_accepted_at", "bidder_id", "accepted_at"),
    )
    lot_id: Mapped[UUID] = mapped_column(ForeignKey("lots.id", ondelete="RESTRICT"))
    bidder_id: Mapped[UUID] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"))
    sequence: Mapped[int] = mapped_column(BigInteger)
    amount_cents: Mapped[int] = mapped_column(BigInteger)
    accepted_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    previous_hash: Mapped[str] = mapped_column(String(64))
    record_hash: Mapped[str] = mapped_column(String(64))
    signature: Mapped[str] = mapped_column(String(64))
    key_version: Mapped[int] = mapped_column(Integer)


class WalletReservation(UUIDPrimaryKey, CreatedAt, Base):
    __tablename__ = "wallet_reservations"
    __table_args__ = (
        ForeignKeyConstraint(
            ["lot_id", "bid_id"], ["bids.lot_id", "bids.id"], ondelete="RESTRICT"
        ),
        CheckConstraint("amount_cents > 0", name="positive_amount"),
        CheckConstraint(
            "status IN ('active', 'released', 'captured')", name="valid_status"
        ),
        CheckConstraint(
            "(status = 'active') = (released_at IS NULL)", name="release_timestamp"
        ),
        Index(
            "uq_reservations_active_lot",
            "lot_id",
            unique=True,
            postgresql_where=text("status = 'active'"),
        ),
        Index("ix_reservations_wallet_status", "wallet_id", "status"),
    )
    lot_id: Mapped[UUID] = mapped_column(ForeignKey("lots.id", ondelete="RESTRICT"))
    wallet_id: Mapped[UUID] = mapped_column(
        ForeignKey("wallets.id", ondelete="RESTRICT")
    )
    bid_id: Mapped[UUID] = mapped_column(unique=True)
    amount_cents: Mapped[int] = mapped_column(BigInteger)
    status: Mapped[str] = mapped_column(String(20), server_default="active")
    released_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class WalletEntry(UUIDPrimaryKey, CreatedAt, Base):
    __tablename__ = "wallet_entries"
    __table_args__ = (
        CheckConstraint("amount_cents > 0", name="positive_amount"),
        CheckConstraint(
            "type IN ('deposit', 'reserve', 'release', 'debit', 'credit')",
            name="valid_type",
        ),
        CheckConstraint(
            "(type = 'deposit' AND lot_id IS NULL AND bid_id IS NULL "
            "AND request_hash IS NOT NULL) OR "
            "(type <> 'deposit' AND lot_id IS NOT NULL AND bid_id IS NOT NULL)",
            name="entry_references",
        ),
        ForeignKeyConstraint(
            ["lot_id", "bid_id"], ["bids.lot_id", "bids.id"], ondelete="RESTRICT"
        ),
        Index("ix_entries_wallet_created_at", "wallet_id", "created_at"),
    )
    wallet_id: Mapped[UUID] = mapped_column(
        ForeignKey("wallets.id", ondelete="RESTRICT")
    )
    lot_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("lots.id", ondelete="RESTRICT")
    )
    bid_id: Mapped[UUID | None] = mapped_column()
    type: Mapped[str] = mapped_column(String(20))
    amount_cents: Mapped[int] = mapped_column(BigInteger)
    operation_key: Mapped[str] = mapped_column(String(255), unique=True)
    request_hash: Mapped[str | None] = mapped_column(String(64))


class Settlement(UUIDPrimaryKey, Base):
    __tablename__ = "settlements"
    __table_args__ = (
        ForeignKeyConstraint(
            ["lot_id", "winning_bid_id"],
            ["bids.lot_id", "bids.id"],
            ondelete="RESTRICT",
        ),
        CheckConstraint("amount_cents > 0", name="positive_amount"),
        CheckConstraint("buyer_wallet_id <> seller_wallet_id", name="distinct_wallets"),
    )
    lot_id: Mapped[UUID] = mapped_column(
        ForeignKey("lots.id", ondelete="RESTRICT"), unique=True
    )
    winning_bid_id: Mapped[UUID] = mapped_column(unique=True)
    buyer_wallet_id: Mapped[UUID] = mapped_column(
        ForeignKey("wallets.id", ondelete="RESTRICT")
    )
    seller_wallet_id: Mapped[UUID] = mapped_column(
        ForeignKey("wallets.id", ondelete="RESTRICT")
    )
    amount_cents: Mapped[int] = mapped_column(BigInteger)
    settled_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )


class Receipt(UUIDPrimaryKey, CreatedAt, Base):
    __tablename__ = "receipts"
    settlement_id: Mapped[UUID] = mapped_column(
        ForeignKey("settlements.id", ondelete="RESTRICT"), unique=True
    )
    snapshot: Mapped[dict] = mapped_column(JSONB)


class AuditHead(Base):
    __tablename__ = "audit_heads"
    __table_args__ = (
        CheckConstraint(
            "last_sequence >= 0 AND key_version > 0", name="valid_sequence_key"
        ),
        CheckConstraint(
            "last_hash ~ '^[0-9a-f]{64}$' AND signature ~ '^[0-9a-f]{64}$'",
            name="valid_hashes",
        ),
    )
    lot_id: Mapped[UUID] = mapped_column(
        ForeignKey("lots.id", ondelete="RESTRICT"), primary_key=True
    )
    last_sequence: Mapped[int] = mapped_column(BigInteger)
    last_hash: Mapped[str] = mapped_column(String(64))
    signature: Mapped[str] = mapped_column(String(64))
    key_version: Mapped[int] = mapped_column(Integer)


class OutboxEvent(UUIDPrimaryKey, CreatedAt, Base):
    __tablename__ = "outbox_events"
    __table_args__ = (
        CheckConstraint(
            "aggregate_version > 0 AND attempts >= 0", name="valid_version_attempts"
        ),
        CheckConstraint(
            "event_type IN ('BidAccepted', 'AuctionExtended', 'AuctionClosed')",
            name="valid_event_type",
        ),
        UniqueConstraint("lot_id", "aggregate_version", "event_type"),
        Index(
            "ix_outbox_pending",
            "next_attempt_at",
            "created_at",
            postgresql_where=text("published_at IS NULL"),
        ),
        Index(
            "ix_outbox_published",
            "published_at",
            "id",
            postgresql_where=text("published_at IS NOT NULL"),
        ),
    )
    lot_id: Mapped[UUID] = mapped_column(ForeignKey("lots.id", ondelete="RESTRICT"))
    aggregate_version: Mapped[int] = mapped_column(BigInteger)
    event_type: Mapped[str] = mapped_column(String(40))
    payload: Mapped[dict] = mapped_column(JSONB)
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    attempts: Mapped[int] = mapped_column(Integer, server_default="0")
    next_attempt_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
