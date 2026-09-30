"""Operational records: collection runs, processing steps, and errors.

These tables grow quickly, so they use compact auto-incrementing integer ids
and are designed to be cleaned up by a retention job (Phase 11).
Never write secrets into ``message``, ``details`` or ``stack_trace``; use
``ErrorLogRepository.record`` / ``redact_text`` which scrub credentials.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Identity,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, UUIDPrimaryKeyMixin
from app.models.enums import JobStatus, JobTrigger, ProcessingStep, Severity, StepStatus, db_enum


class CollectionJob(UUIDPrimaryKeyMixin, Base):
    """One run of a collector or scheduled task (e.g. "fetch source X")."""

    __tablename__ = "collection_jobs"
    __table_args__ = (
        CheckConstraint(
            "items_found >= 0 AND items_created >= 0 AND items_updated >= 0 AND items_failed >= 0",
            name="counts_nonneg",
        ),
        CheckConstraint(
            "finished_at IS NULL OR started_at IS NULL OR finished_at >= started_at",
            name="times_order",
        ),
        Index("ix_collection_jobs_source_recent", "source_id", text("created_at DESC")),
        Index("ix_collection_jobs_status_recent", "status", text("created_at DESC")),
    )

    job_type: Mapped[str] = mapped_column(String(50))  # e.g. fetch_source, fetch_arxiv
    source_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("sources.id", ondelete="SET NULL")
    )
    status: Mapped[JobStatus] = mapped_column(
        db_enum(JobStatus, "job_status"), server_default=JobStatus.QUEUED.value
    )
    trigger: Mapped[JobTrigger] = mapped_column(
        db_enum(JobTrigger, "job_trigger"), server_default=JobTrigger.SCHEDULE.value
    )
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    items_found: Mapped[int] = mapped_column(Integer, server_default="0")
    items_created: Mapped[int] = mapped_column(Integer, server_default="0")
    items_updated: Mapped[int] = mapped_column(Integer, server_default="0")
    items_failed: Mapped[int] = mapped_column(Integer, server_default="0")
    error_message: Mapped[str | None] = mapped_column(Text)
    details: Mapped[dict[str, Any]] = mapped_column(JSONB, server_default=text("'{}'::jsonb"))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=text("now()")
    )


class ProcessingLog(Base):
    """One step of the content pipeline for one item (fetch, summarize, embed …).

    AI steps also record provider, model, token counts and cost, which powers
    the AI cost dashboard and daily budget cap.
    """

    __tablename__ = "processing_logs"
    __table_args__ = (
        CheckConstraint("input_tokens IS NULL OR input_tokens >= 0", name="input_tokens_nonneg"),
        CheckConstraint("output_tokens IS NULL OR output_tokens >= 0", name="output_tokens_nonneg"),
        CheckConstraint("cost_usd IS NULL OR cost_usd >= 0", name="cost_nonneg"),
        Index("ix_processing_logs_content_recent", "content_id", text("created_at DESC")),
        Index("ix_processing_logs_step_recent", "step", "status", text("created_at DESC")),
        Index("ix_processing_logs_created_at", "created_at"),
    )

    id: Mapped[int] = mapped_column(BigInteger, Identity(), primary_key=True)
    content_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("content_items.id", ondelete="SET NULL")
    )
    collection_job_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("collection_jobs.id", ondelete="SET NULL"), index=True
    )
    step: Mapped[ProcessingStep] = mapped_column(db_enum(ProcessingStep, "processing_step"))
    status: Mapped[StepStatus] = mapped_column(db_enum(StepStatus, "step_status"))
    provider: Mapped[str | None] = mapped_column(String(50))
    model: Mapped[str | None] = mapped_column(String(100))
    prompt_version: Mapped[str | None] = mapped_column(String(50))
    input_tokens: Mapped[int | None] = mapped_column(Integer)
    output_tokens: Mapped[int | None] = mapped_column(Integer)
    cost_usd: Mapped[Decimal | None] = mapped_column(Numeric(12, 6))
    duration_ms: Mapped[int | None] = mapped_column(Integer)
    message: Mapped[str | None] = mapped_column(Text)
    details: Mapped[dict[str, Any]] = mapped_column(JSONB, server_default=text("'{}'::jsonb"))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=text("now()")
    )


class ErrorLog(Base):
    """Errors worth keeping beyond the normal logs (for the admin status page)."""

    __tablename__ = "error_logs"
    __table_args__ = (
        Index("ix_error_logs_occurred_at", text("occurred_at DESC")),
        Index("ix_error_logs_component_recent", "component", text("occurred_at DESC")),
        Index(
            "ix_error_logs_unresolved",
            text("occurred_at DESC"),
            postgresql_where=text("resolved_at IS NULL"),
        ),
    )

    id: Mapped[int] = mapped_column(BigInteger, Identity(), primary_key=True)
    occurred_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=text("now()")
    )
    severity: Mapped[Severity] = mapped_column(db_enum(Severity, "severity"))
    component: Mapped[str] = mapped_column(String(50))  # api, worker, collector, ai …
    error_type: Mapped[str] = mapped_column(String(200))
    message: Mapped[str] = mapped_column(Text)
    stack_trace: Mapped[str | None] = mapped_column(Text)
    context: Mapped[dict[str, Any]] = mapped_column(JSONB, server_default=text("'{}'::jsonb"))
    request_id: Mapped[str | None] = mapped_column(String(128))
    collection_job_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("collection_jobs.id", ondelete="SET NULL"), index=True
    )
    content_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("content_items.id", ondelete="SET NULL"), index=True
    )
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
