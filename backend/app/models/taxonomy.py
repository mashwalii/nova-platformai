"""Reference data: where content comes from and how it is organised."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    SmallInteger,
    String,
    Text,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin
from app.models.enums import ContentType, Language, SourceKind, db_enum


class Source(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """A place content is collected from (RSS feed, arXiv, a job board, manual entry).

    ``config`` holds NON-secret settings only (e.g. arXiv categories). API keys
    live in environment variables, never in the database.
    """

    __tablename__ = "sources"
    __table_args__ = (
        CheckConstraint("trust_level BETWEEN 1 AND 5", name="trust_level_range"),
        CheckConstraint("fetch_interval_minutes >= 5", name="fetch_interval_min"),
        CheckConstraint("consecutive_failures >= 0", name="consecutive_failures_nonneg"),
        Index("ix_sources_active_kind", "is_active", "kind"),
    )

    slug: Mapped[str] = mapped_column(String(100), unique=True)
    name: Mapped[str] = mapped_column(String(200))
    kind: Mapped[SourceKind] = mapped_column(db_enum(SourceKind, "source_kind"))
    homepage_url: Mapped[str | None] = mapped_column(Text)
    feed_url: Mapped[str | None] = mapped_column(Text, unique=True)
    language: Mapped[Language] = mapped_column(
        db_enum(Language, "language"), server_default=Language.EN.value
    )
    trust_level: Mapped[int] = mapped_column(SmallInteger, server_default="3")
    is_active: Mapped[bool] = mapped_column(Boolean, server_default=text("true"))
    fetch_interval_minutes: Mapped[int] = mapped_column(Integer, server_default="60")
    config: Mapped[dict[str, Any]] = mapped_column(JSONB, server_default=text("'{}'::jsonb"))
    # HTTP caching and health (updated by collectors)
    etag: Mapped[str | None] = mapped_column(Text)
    last_modified: Mapped[str | None] = mapped_column(Text)
    last_fetched_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_success_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    consecutive_failures: Mapped[int] = mapped_column(Integer, server_default="0")


class Author(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """A person who wrote an article or paper."""

    __tablename__ = "authors"

    slug: Mapped[str] = mapped_column(String(200), unique=True)
    name: Mapped[str] = mapped_column(String(200))
    name_ar: Mapped[str | None] = mapped_column(String(200))
    affiliation: Mapped[str | None] = mapped_column(String(300))
    orcid: Mapped[str | None] = mapped_column(String(19), unique=True)
    homepage_url: Mapped[str | None] = mapped_column(Text)


class Category(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Curated, hierarchical taxonomy (e.g. "AI Research" → "Computer Vision").

    ``content_type`` limits a category to one kind of content (e.g. course
    categories); NULL means it applies to all.
    """

    __tablename__ = "categories"
    __table_args__ = (Index("ix_categories_type_sort", "content_type", "sort_order"),)

    slug: Mapped[str] = mapped_column(String(100), unique=True)
    name_en: Mapped[str] = mapped_column(String(120))
    name_ar: Mapped[str] = mapped_column(String(120))
    description_en: Mapped[str | None] = mapped_column(Text)
    description_ar: Mapped[str | None] = mapped_column(Text)
    parent_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("categories.id", ondelete="SET NULL"), index=True
    )
    content_type: Mapped[ContentType | None] = mapped_column(db_enum(ContentType, "content_type"))
    sort_order: Mapped[int] = mapped_column(Integer, server_default="0")
    is_active: Mapped[bool] = mapped_column(Boolean, server_default=text("true"))

    parent: Mapped[Category | None] = relationship(remote_side="Category.id", lazy="raise")


class Tag(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Free-form keyword (e.g. "llama", "rlhf"); many per item."""

    __tablename__ = "tags"

    slug: Mapped[str] = mapped_column(String(100), unique=True)
    name_en: Mapped[str] = mapped_column(String(120))
    name_ar: Mapped[str | None] = mapped_column(String(120))
