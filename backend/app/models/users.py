"""Users and everything personal to them.

``users.id`` is the SAME id Supabase Auth gives the person (``auth.users.id``).
There is deliberately no database-level link to Supabase's ``auth`` schema, so
the schema also works on plain PostgreSQL (local development, tests); the
backend keeps the two in sync (Phase 13). Passwords are never stored here —
Supabase Auth handles them.
"""

from __future__ import annotations

import uuid
from datetime import datetime, time
from decimal import Decimal

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Numeric,
    String,
    Text,
    Time,
    func,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin
from app.models.enums import (
    DigestFrequency,
    Language,
    NotificationKind,
    Theme,
    UserRole,
    UserStatus,
    db_enum,
)


class User(TimestampMixin, Base):
    __tablename__ = "users"
    __table_args__ = (
        # Case-insensitive unique e-mail.
        Index("uq_users_email_lower", func.lower(text("email")), unique=True),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True)  # = Supabase auth user id
    email: Mapped[str | None] = mapped_column(String(320))
    display_name: Mapped[str | None] = mapped_column(String(100))
    role: Mapped[UserRole] = mapped_column(
        db_enum(UserRole, "user_role"), server_default=UserRole.USER.value
    )
    status: Mapped[UserStatus] = mapped_column(
        db_enum(UserStatus, "user_status"), server_default=UserStatus.ACTIVE.value
    )
    onboarding_completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_seen_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    preferences: Mapped[UserPreferences | None] = relationship(back_populates="user", lazy="raise")


class UserPreferences(TimestampMixin, Base):
    """One row per user: language, theme, notification and digest choices."""

    __tablename__ = "user_preferences"

    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
    )
    language: Mapped[Language] = mapped_column(
        db_enum(Language, "language"), server_default=Language.EN.value
    )
    theme: Mapped[Theme] = mapped_column(db_enum(Theme, "theme"), server_default=Theme.SYSTEM.value)
    timezone: Mapped[str] = mapped_column(String(64), server_default="UTC")
    email_digest: Mapped[DigestFrequency] = mapped_column(
        db_enum(DigestFrequency, "digest_frequency"), server_default=DigestFrequency.OFF.value
    )
    notify_deadlines: Mapped[bool] = mapped_column(Boolean, server_default=text("true"))
    notify_topic_updates: Mapped[bool] = mapped_column(Boolean, server_default=text("true"))
    quiet_hours_start: Mapped[time | None] = mapped_column(Time)
    quiet_hours_end: Mapped[time | None] = mapped_column(Time)

    user: Mapped[User] = relationship(back_populates="preferences", lazy="raise")


class UserInterest(Base):
    """Categories a user follows, with a weight (explicit choice or learned)."""

    __tablename__ = "user_interests"
    __table_args__ = (CheckConstraint("weight BETWEEN 0 AND 1", name="weight_range"),)

    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
    )
    category_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("categories.id", ondelete="CASCADE"), primary_key=True, index=True
    )
    weight: Mapped[Decimal] = mapped_column(Numeric(4, 3), server_default="1")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=text("now()")
    )


class SavedItem(Base):
    """An item a user saved (any content type)."""

    __tablename__ = "saved_items"
    __table_args__ = (Index("ix_saved_items_user_recent", "user_id", text("created_at DESC")),)

    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
    )
    content_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("content_items.id", ondelete="CASCADE"), primary_key=True, index=True
    )
    note: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=text("now()")
    )


class Notification(UUIDPrimaryKeyMixin, Base):
    """An in-app notification (optionally also e-mailed)."""

    __tablename__ = "notifications"
    __table_args__ = (
        Index("ix_notifications_user_recent", "user_id", text("created_at DESC")),
        # Fast "unread count" for the bell icon.
        Index(
            "ix_notifications_user_unread",
            "user_id",
            postgresql_where=text("read_at IS NULL"),
        ),
    )

    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    kind: Mapped[NotificationKind] = mapped_column(db_enum(NotificationKind, "notification_kind"))
    content_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("content_items.id", ondelete="SET NULL"), index=True
    )
    title_en: Mapped[str] = mapped_column(String(200))
    title_ar: Mapped[str | None] = mapped_column(String(200))
    body_en: Mapped[str | None] = mapped_column(Text)
    body_ar: Mapped[str | None] = mapped_column(Text)
    link_path: Mapped[str | None] = mapped_column(String(300))
    read_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    emailed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=text("now()")
    )
