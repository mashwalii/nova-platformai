"""Allowed values for status/type columns.

Stored as short text with a CHECK constraint (not native PostgreSQL enums),
so adding a value later is a simple migration.
"""

from __future__ import annotations

from enum import StrEnum
from typing import Any

from sqlalchemy import Enum


def db_enum(enum_cls: type[StrEnum], name: str) -> Enum:
    """Column type storing the enum's *values* as VARCHAR + CHECK constraint."""
    return Enum(
        enum_cls,
        name=name,
        native_enum=False,
        create_constraint=True,
        length=32,
        values_callable=lambda members: [m.value for m in members],
        validate_strings=True,
    )


class Language(StrEnum):
    EN = "en"
    AR = "ar"


class ContentType(StrEnum):
    ARTICLE = "article"
    PAPER = "paper"
    COURSE = "course"
    OPPORTUNITY = "opportunity"
    TOOL = "tool"


class ContentStatus(StrEnum):
    DRAFT = "draft"  # created by an editor, not ready
    INGESTED = "ingested"  # collected from a source, not processed yet
    PROCESSING = "processing"  # AI pipeline running
    NEEDS_REVIEW = "needs_review"  # waiting for a human
    PUBLISHED = "published"  # visible on the site
    REJECTED = "rejected"  # not relevant / low quality
    ARCHIVED = "archived"  # no longer shown (e.g. expired opportunity)


class SourceKind(StrEnum):
    RSS = "rss"
    ARXIV = "arxiv"
    API = "api"
    JOB_BOARD = "job_board"
    WEBSITE = "website"
    MANUAL = "manual"


class OpportunityType(StrEnum):
    SCHOLARSHIP = "scholarship"
    FELLOWSHIP = "fellowship"
    INTERNSHIP = "internship"
    JOB = "job"
    COMPETITION = "competition"
    HACKATHON = "hackathon"
    BOOTCAMP = "bootcamp"
    RESEARCH = "research"


class EmploymentType(StrEnum):
    FULL_TIME = "full_time"
    PART_TIME = "part_time"
    CONTRACT = "contract"
    TEMPORARY = "temporary"
    INTERNSHIP = "internship"


class CourseLevel(StrEnum):
    BEGINNER = "beginner"
    INTERMEDIATE = "intermediate"
    ADVANCED = "advanced"
    ALL_LEVELS = "all_levels"


class ToolPricing(StrEnum):
    FREE = "free"
    FREEMIUM = "freemium"
    PAID = "paid"
    OPEN_SOURCE = "open_source"
    ENTERPRISE = "enterprise"


class TagOrigin(StrEnum):
    EDITOR = "editor"
    AI = "ai"
    SOURCE = "source"


class SummaryKind(StrEnum):
    ARTICLE_BRIEF = "article_brief"  # TL;DR, takeaways, why it matters, …
    PAPER_ANALYSIS = "paper_analysis"
    SHORT = "short"


class EmbeddingKind(StrEnum):
    DOCUMENT = "document"  # one vector for the whole item
    CHUNK = "chunk"  # one vector per passage (RAG)


class UserRole(StrEnum):
    USER = "user"
    EDITOR = "editor"
    ADMIN = "admin"


class UserStatus(StrEnum):
    ACTIVE = "active"
    SUSPENDED = "suspended"
    DELETED = "deleted"


class Theme(StrEnum):
    LIGHT = "light"
    DARK = "dark"
    SYSTEM = "system"


class DigestFrequency(StrEnum):
    OFF = "off"
    DAILY = "daily"
    WEEKLY = "weekly"


class NotificationKind(StrEnum):
    DEADLINE_REMINDER = "deadline_reminder"
    TOPIC_UPDATE = "topic_update"
    DAILY_BRIEF = "daily_brief"
    SYSTEM = "system"


class BriefStatus(StrEnum):
    DRAFT = "draft"
    PUBLISHED = "published"
    ARCHIVED = "archived"


class JobStatus(StrEnum):
    QUEUED = "queued"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    CANCELLED = "cancelled"


class JobTrigger(StrEnum):
    SCHEDULE = "schedule"
    MANUAL = "manual"
    RETRY = "retry"


class ProcessingStep(StrEnum):
    FETCH = "fetch"
    EXTRACT = "extract"
    DEDUPLICATE = "deduplicate"
    CLASSIFY = "classify"
    SUMMARIZE = "summarize"
    TRANSLATE = "translate"
    EMBED = "embed"
    PUBLISH = "publish"


class StepStatus(StrEnum):
    STARTED = "started"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    SKIPPED = "skipped"


class Severity(StrEnum):
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


def enum_values(enum_cls: type[StrEnum]) -> list[Any]:
    return [member.value for member in enum_cls]
