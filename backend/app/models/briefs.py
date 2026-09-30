"""Daily AI briefings."""

from __future__ import annotations

import uuid
from datetime import date, datetime

from sqlalchemy import (
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    SmallInteger,
    String,
    Text,
    UniqueConstraint,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin
from app.models.enums import BriefStatus, db_enum


class DailyBrief(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """One briefing per day, in English and Arabic."""

    __tablename__ = "daily_briefs"

    brief_date: Mapped[date] = mapped_column(Date, unique=True)
    status: Mapped[BriefStatus] = mapped_column(
        db_enum(BriefStatus, "brief_status"), server_default=BriefStatus.DRAFT.value
    )
    headline_en: Mapped[str] = mapped_column(String(300))
    headline_ar: Mapped[str | None] = mapped_column(String(300))
    intro_en: Mapped[str | None] = mapped_column(Text)
    intro_ar: Mapped[str | None] = mapped_column(Text)
    signal_en: Mapped[str | None] = mapped_column(Text)  # "one essential signal"
    signal_ar: Mapped[str | None] = mapped_column(Text)
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    model: Mapped[str | None] = mapped_column(String(100))
    processing_log_id: Mapped[int | None] = mapped_column(
        ForeignKey("processing_logs.id", ondelete="SET NULL"), index=True
    )

    items: Mapped[list[DailyBriefItem]] = relationship(
        back_populates="brief", order_by="DailyBriefItem.position", lazy="raise"
    )


class DailyBriefItem(UUIDPrimaryKeyMixin, Base):
    """A story in a briefing, in order."""

    __tablename__ = "daily_brief_items"
    __table_args__ = (
        UniqueConstraint("brief_id", "position", name="uq_daily_brief_items_position"),
        UniqueConstraint("brief_id", "content_id", name="uq_daily_brief_items_content"),
        CheckConstraint("position >= 1", name="position_pos"),
    )

    brief_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("daily_briefs.id", ondelete="CASCADE"))
    content_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("content_items.id", ondelete="CASCADE"), index=True
    )
    position: Mapped[int] = mapped_column(SmallInteger)
    blurb_en: Mapped[str | None] = mapped_column(Text)
    blurb_ar: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=text("now()")
    )

    brief: Mapped[DailyBrief] = relationship(back_populates="items", lazy="raise")
