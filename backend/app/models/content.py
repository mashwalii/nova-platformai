"""Content: one shared ``content_items`` row per item + a detail table per type.

Every article, paper, course, opportunity and AI tool has exactly one row in
``content_items`` (title, summary, status, dates …). Type-specific fields live
in a 1-to-1 detail table whose primary key is also the content item's id.
This lets saving, search, embeddings, notifications and briefs work the same
way for every kind of content.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import (
    ARRAY,
    Boolean,
    CheckConstraint,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    SmallInteger,
    String,
    Text,
    UniqueConstraint,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin
from app.models.enums import (
    ContentStatus,
    ContentType,
    CourseLevel,
    EmploymentType,
    Language,
    OpportunityType,
    TagOrigin,
    ToolPricing,
    db_enum,
)
from app.models.taxonomy import Author, Category, Source, Tag


class ContentItem(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "content_items"
    __table_args__ = (
        UniqueConstraint("content_type", "slug", name="uq_content_items_type_slug"),
        CheckConstraint("title_en IS NOT NULL OR title_ar IS NOT NULL", name="has_title"),
        CheckConstraint(
            "importance IS NULL OR importance BETWEEN 1 AND 5", name="importance_range"
        ),
        CheckConstraint("view_count >= 0", name="view_count_nonneg"),
        # Main listing query: published items of a type, newest first.
        Index("ix_content_items_listing", "content_type", "status", text("published_at DESC")),
        Index(
            "ix_content_items_featured",
            "content_type",
            text("published_at DESC"),
            postgresql_where=text("is_featured AND status = 'published'"),
        ),
        # Fuzzy title search (typos, partial words) via the pg_trgm extension.
        Index(
            "ix_content_items_title_en_trgm",
            "title_en",
            postgresql_using="gin",
            postgresql_ops={"title_en": "gin_trgm_ops"},
        ),
        Index(
            "ix_content_items_title_ar_trgm",
            "title_ar",
            postgresql_using="gin",
            postgresql_ops={"title_ar": "gin_trgm_ops"},
        ),
    )

    content_type: Mapped[ContentType] = mapped_column(db_enum(ContentType, "content_type"))
    slug: Mapped[str] = mapped_column(String(200))
    status: Mapped[ContentStatus] = mapped_column(
        db_enum(ContentStatus, "content_status"), server_default=ContentStatus.DRAFT.value
    )
    source_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("sources.id", ondelete="SET NULL"), index=True
    )
    category_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("categories.id", ondelete="SET NULL"), index=True
    )
    original_language: Mapped[Language] = mapped_column(
        db_enum(Language, "language"), server_default=Language.EN.value
    )
    title_en: Mapped[str | None] = mapped_column(Text)
    title_ar: Mapped[str | None] = mapped_column(Text)
    summary_en: Mapped[str | None] = mapped_column(Text)
    summary_ar: Mapped[str | None] = mapped_column(Text)
    canonical_url: Mapped[str | None] = mapped_column(Text)
    # SHA-256 of the normalized URL: stops the same link being stored twice.
    url_hash: Mapped[str | None] = mapped_column(String(64), unique=True)
    image_url: Mapped[str | None] = mapped_column(Text)
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    source_updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    importance: Mapped[int | None] = mapped_column(SmallInteger)
    is_featured: Mapped[bool] = mapped_column(Boolean, server_default=text("false"))
    is_trending: Mapped[bool] = mapped_column(Boolean, server_default=text("false"))
    trending_score: Mapped[float] = mapped_column(Float, server_default="0")
    view_count: Mapped[int] = mapped_column(Integer, server_default="0")
    ai_generated: Mapped[bool] = mapped_column(Boolean, server_default=text("false"))
    extra: Mapped[dict[str, Any]] = mapped_column(JSONB, server_default=text("'{}'::jsonb"))

    source: Mapped[Source | None] = relationship(lazy="raise")
    category: Mapped[Category | None] = relationship(lazy="raise")
    article: Mapped[Article | None] = relationship(back_populates="content", lazy="raise")
    paper: Mapped[Paper | None] = relationship(back_populates="content", lazy="raise")
    course: Mapped[Course | None] = relationship(back_populates="content", lazy="raise")
    opportunity: Mapped[Opportunity | None] = relationship(back_populates="content", lazy="raise")
    tool: Mapped[AITool | None] = relationship(back_populates="content", lazy="raise")


def _content_pk() -> Mapped[uuid.UUID]:
    return mapped_column(ForeignKey("content_items.id", ondelete="CASCADE"), primary_key=True)


class Article(TimestampMixin, Base):
    """News article details. ``body_text`` is for internal processing only."""

    __tablename__ = "articles"
    __table_args__ = (CheckConstraint("reading_minutes > 0", name="reading_minutes_pos"),)

    content_id: Mapped[uuid.UUID] = _content_pk()
    body_text: Mapped[str | None] = mapped_column(Text)
    word_count: Mapped[int | None] = mapped_column(Integer)
    reading_minutes: Mapped[int | None] = mapped_column(SmallInteger)
    body_retained_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    content: Mapped[ContentItem] = relationship(back_populates="article", lazy="raise")


class Paper(TimestampMixin, Base):
    """Scientific paper details."""

    __tablename__ = "papers"

    content_id: Mapped[uuid.UUID] = _content_pk()
    arxiv_id: Mapped[str | None] = mapped_column(String(32), unique=True)
    doi: Mapped[str | None] = mapped_column(String(255), unique=True)
    abstract: Mapped[str | None] = mapped_column(Text)
    subject_areas: Mapped[list[str]] = mapped_column(
        ARRAY(String(32)), server_default=text("'{}'::varchar[]")
    )
    pdf_url: Mapped[str | None] = mapped_column(Text)
    code_url: Mapped[str | None] = mapped_column(Text)
    venue: Mapped[str | None] = mapped_column(String(200))
    citation_count: Mapped[int | None] = mapped_column(Integer)
    full_text: Mapped[str | None] = mapped_column(Text)
    full_text_extracted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    license: Mapped[str | None] = mapped_column(String(100))

    content: Mapped[ContentItem] = relationship(back_populates="paper", lazy="raise")


class Course(TimestampMixin, Base):
    """Course details."""

    __tablename__ = "courses"
    __table_args__ = (
        CheckConstraint("duration_hours IS NULL OR duration_hours > 0", name="duration_pos"),
    )

    content_id: Mapped[uuid.UUID] = _content_pk()
    provider: Mapped[str] = mapped_column(String(200))
    level: Mapped[CourseLevel] = mapped_column(
        db_enum(CourseLevel, "course_level"), server_default=CourseLevel.ALL_LEVELS.value
    )
    duration_hours: Mapped[Decimal | None] = mapped_column(Numeric(6, 1))
    duration_label_en: Mapped[str | None] = mapped_column(String(100))
    duration_label_ar: Mapped[str | None] = mapped_column(String(100))
    instruction_language_en: Mapped[str | None] = mapped_column(String(100))
    instruction_language_ar: Mapped[str | None] = mapped_column(String(100))
    is_free: Mapped[bool] = mapped_column(Boolean, server_default=text("true"), index=True)
    has_certificate: Mapped[bool] = mapped_column(Boolean, server_default=text("false"))
    enrollment_url: Mapped[str | None] = mapped_column(Text)

    content: Mapped[ContentItem] = relationship(back_populates="course", lazy="raise")


class Opportunity(TimestampMixin, Base):
    """Scholarships, fellowships, internships, jobs, competitions, hackathons, …

    One table for all opportunity types: most fields are shared, and
    job-only fields (employment type, seniority, salary) are simply empty for
    other types.
    """

    __tablename__ = "opportunities"
    __table_args__ = (
        CheckConstraint(
            "starts_at IS NULL OR ends_at IS NULL OR starts_at <= ends_at", name="dates_order"
        ),
        Index("ix_opportunities_type_deadline", "opportunity_type", "deadline_at"),
    )

    content_id: Mapped[uuid.UUID] = _content_pk()
    opportunity_type: Mapped[OpportunityType] = mapped_column(
        db_enum(OpportunityType, "opportunity_type")
    )
    organization: Mapped[str] = mapped_column(String(200))
    location_en: Mapped[str | None] = mapped_column(String(200))
    location_ar: Mapped[str | None] = mapped_column(String(200))
    country_code: Mapped[str | None] = mapped_column(String(2))
    is_remote: Mapped[bool] = mapped_column(Boolean, server_default=text("false"))
    eligibility_en: Mapped[str | None] = mapped_column(Text)
    eligibility_ar: Mapped[str | None] = mapped_column(Text)
    deadline_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    starts_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    ends_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    apply_url: Mapped[str | None] = mapped_column(Text)
    funding_en: Mapped[str | None] = mapped_column(Text)
    funding_ar: Mapped[str | None] = mapped_column(Text)
    # Jobs / internships
    employment_type: Mapped[EmploymentType | None] = mapped_column(
        db_enum(EmploymentType, "employment_type")
    )
    seniority: Mapped[str | None] = mapped_column(String(50))
    salary_text: Mapped[str | None] = mapped_column(String(200))

    content: Mapped[ContentItem] = relationship(back_populates="opportunity", lazy="raise")


class AITool(TimestampMixin, Base):
    """AI tools directory entry."""

    __tablename__ = "ai_tools"

    content_id: Mapped[uuid.UUID] = _content_pk()
    website_url: Mapped[str] = mapped_column(Text)
    pricing: Mapped[ToolPricing] = mapped_column(db_enum(ToolPricing, "tool_pricing"))
    vendor: Mapped[str | None] = mapped_column(String(200))
    platforms: Mapped[list[str]] = mapped_column(
        ARRAY(String(40)), server_default=text("'{}'::varchar[]")
    )
    has_api: Mapped[bool] = mapped_column(Boolean, server_default=text("false"))
    repository_url: Mapped[str | None] = mapped_column(Text)

    content: Mapped[ContentItem] = relationship(back_populates="tool", lazy="raise")


class LearningPath(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """An ordered path of steps (e.g. "AI Engineer": Python → Data Science → …)."""

    __tablename__ = "learning_paths"

    slug: Mapped[str] = mapped_column(String(100), unique=True)
    title_en: Mapped[str] = mapped_column(String(200))
    title_ar: Mapped[str] = mapped_column(String(200))
    description_en: Mapped[str | None] = mapped_column(Text)
    description_ar: Mapped[str | None] = mapped_column(Text)
    level: Mapped[CourseLevel] = mapped_column(
        db_enum(CourseLevel, "course_level"), server_default=CourseLevel.ALL_LEVELS.value
    )
    sort_order: Mapped[int] = mapped_column(Integer, server_default="0")
    is_published: Mapped[bool] = mapped_column(Boolean, server_default=text("true"))

    steps: Mapped[list[LearningPathStep]] = relationship(
        back_populates="path", order_by="LearningPathStep.position", lazy="raise"
    )


class LearningPathStep(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "learning_path_steps"
    __table_args__ = (
        UniqueConstraint("path_id", "position", name="uq_learning_path_steps_position"),
        CheckConstraint("position >= 1", name="position_pos"),
    )

    path_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("learning_paths.id", ondelete="CASCADE"))
    position: Mapped[int] = mapped_column(SmallInteger)
    title_en: Mapped[str] = mapped_column(String(200))
    title_ar: Mapped[str] = mapped_column(String(200))
    # Optional link to a concrete course for this step.
    course_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("content_items.id", ondelete="SET NULL"), index=True
    )

    path: Mapped[LearningPath] = relationship(back_populates="steps", lazy="raise")


class ContentAuthor(Base):
    """Which authors wrote which item (ordered)."""

    __tablename__ = "content_authors"
    __table_args__ = (CheckConstraint("position >= 1", name="position_pos"),)

    content_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("content_items.id", ondelete="CASCADE"), primary_key=True
    )
    author_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("authors.id", ondelete="CASCADE"), primary_key=True, index=True
    )
    position: Mapped[int] = mapped_column(SmallInteger, server_default="1")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=text("now()")
    )

    author: Mapped[Author] = relationship(lazy="raise")


class ContentTag(Base):
    """Tags on an item, with who added them and (for AI) how confident it was."""

    __tablename__ = "content_tags"
    __table_args__ = (
        CheckConstraint(
            "confidence IS NULL OR confidence BETWEEN 0 AND 1", name="confidence_range"
        ),
    )

    content_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("content_items.id", ondelete="CASCADE"), primary_key=True
    )
    tag_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("tags.id", ondelete="CASCADE"), primary_key=True, index=True
    )
    origin: Mapped[TagOrigin] = mapped_column(
        db_enum(TagOrigin, "tag_origin"), server_default=TagOrigin.EDITOR.value
    )
    confidence: Mapped[Decimal | None] = mapped_column(Numeric(4, 3))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=text("now()")
    )

    tag: Mapped[Tag] = relationship(lazy="raise")
