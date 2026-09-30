"""Shape of the development seed file (``app/seed/data/dev_seed.json``).

The file is validated completely — including every cross-reference such as
"this article's category exists" — before anything is written.
"""

from __future__ import annotations

from datetime import UTC, date, datetime
from decimal import Decimal
from typing import Any, Self

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.models.enums import (
    BriefStatus,
    ContentType,
    CourseLevel,
    DigestFrequency,
    EmploymentType,
    JobStatus,
    JobTrigger,
    Language,
    NotificationKind,
    OpportunityType,
    ProcessingStep,
    Severity,
    SourceKind,
    StepStatus,
    Theme,
    ToolPricing,
    UserRole,
)


class _Model(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class Localized(_Model):
    en: str
    ar: str


class SeedSource(_Model):
    slug: str
    name: str
    kind: SourceKind
    homepage_url: str | None = None
    feed_url: str | None = None
    language: Language = Language.EN
    trust_level: int = Field(default=3, ge=1, le=5)
    is_active: bool = True
    fetch_interval_minutes: int = Field(default=60, ge=5)
    config: dict[str, Any] = Field(default_factory=dict)


class SeedCategory(_Model):
    slug: str
    name: Localized
    content_type: ContentType | None = None
    parent: str | None = None
    sort_order: int = 0


class SeedTag(_Model):
    slug: str
    name: Localized


class SeedAuthor(_Model):
    slug: str
    name: str
    name_ar: str | None = None
    affiliation: str | None = None


class SeedBrief(_Model):
    tldr: str
    key_points: list[str]
    why_it_matters: str
    sections: dict[str, Any]


class _SeedContent(_Model):
    slug: str
    title: Localized
    summary: Localized | None = None
    category: str | None = None
    source: str = "nova-editors"
    tags: list[str] = Field(default_factory=list)
    canonical_url: str | None = None
    published_at: datetime = datetime(2026, 9, 21, 6, 0, tzinfo=UTC)
    importance: int | None = Field(default=None, ge=1, le=5)
    is_featured: bool = False
    extra: dict[str, Any] = Field(default_factory=dict)


class SeedArticle(_SeedContent):
    authors: list[str] = Field(default_factory=list)
    source_updated_at: datetime | None = None
    reading_minutes: int = Field(ge=1)
    view_count: int = Field(default=0, ge=0)
    is_trending: bool = False
    brief: dict[Language, SeedBrief]


class SeedPaper(_SeedContent):
    authors: list[str] = Field(default_factory=list)
    arxiv_id: str | None = None
    pdf_url: str | None = None
    subject_areas: list[str] = Field(default_factory=list)
    venue: str | None = None


class SeedCourse(_SeedContent):
    provider: str
    level: CourseLevel
    duration_label: Localized | None = None
    instruction_language: Localized | None = None
    is_free: bool = True
    enrollment_url: str


class SeedPathStep(_Model):
    title: Localized
    course: str | None = None


class SeedLearningPath(_Model):
    slug: str
    title: Localized
    level: CourseLevel = CourseLevel.ALL_LEVELS
    steps: list[SeedPathStep] = Field(min_length=1)


class SeedOpportunity(_SeedContent):
    opportunity_type: OpportunityType
    organization: str
    location: Localized | None = None
    country_code: str | None = Field(default=None, min_length=2, max_length=2)
    is_remote: bool = False
    eligibility: Localized | None = None
    deadline_at: datetime | None = None
    employment_type: EmploymentType | None = None
    seniority: str | None = None
    salary_text: str | None = None


class SeedTool(_SeedContent):
    website_url: str
    pricing: ToolPricing
    vendor: str | None = None
    platforms: list[str] = Field(default_factory=list)
    has_api: bool = False
    repository_url: str | None = None


class SeedPreferences(_Model):
    language: Language = Language.EN
    theme: Theme = Theme.SYSTEM
    timezone: str = "UTC"
    email_digest: DigestFrequency = DigestFrequency.OFF


class SeedInterest(_Model):
    category: str
    weight: Decimal = Field(default=Decimal(1), ge=0, le=1)


class SeedUser(_Model):
    key: str
    email: str
    display_name: str
    role: UserRole = UserRole.USER
    preferences: SeedPreferences = SeedPreferences()
    interests: list[SeedInterest] = Field(default_factory=list)
    saved: list[str] = Field(default_factory=list)  # "type:slug"


class SeedNotification(_Model):
    user: str
    kind: NotificationKind
    title: Localized
    content: str | None = None
    link_path: str | None = None
    created_at: datetime
    read_at: datetime | None = None


class SeedBriefItem(_Model):
    content: str
    blurb: Localized


class SeedDailyBrief(_Model):
    date: date
    status: BriefStatus
    headline: Localized
    intro: Localized
    signal: Localized
    published_at: datetime | None = None
    items: list[SeedBriefItem]


class SeedCollectionJob(_Model):
    key: str
    job_type: str
    source: str | None = None
    trigger: JobTrigger
    status: JobStatus
    started_at: datetime | None = None
    finished_at: datetime | None = None
    items_found: int = 0
    items_created: int = 0
    items_updated: int = 0
    items_failed: int = 0
    error_message: str | None = None
    details: dict[str, Any] = Field(default_factory=dict)


class SeedProcessingLog(_Model):
    content: str | None = None
    collection_job: str | None = None
    step: ProcessingStep
    status: StepStatus
    provider: str | None = None
    model: str | None = None
    duration_ms: int | None = None


class SeedErrorLog(_Model):
    severity: Severity
    component: str
    error_type: str
    message: str
    collection_job: str | None = None
    occurred_at: datetime
    resolved_at: datetime | None = None


class SeedData(_Model):
    about: str
    sources: list[SeedSource]
    categories: list[SeedCategory]
    tags: list[SeedTag]
    authors: list[SeedAuthor]
    articles: list[SeedArticle]
    papers: list[SeedPaper]
    courses: list[SeedCourse]
    learning_paths: list[SeedLearningPath]
    opportunities: list[SeedOpportunity]
    tools: list[SeedTool]
    users: list[SeedUser]
    notifications: list[SeedNotification]
    daily_briefs: list[SeedDailyBrief]
    collection_jobs: list[SeedCollectionJob]
    processing_logs: list[SeedProcessingLog]
    error_logs: list[SeedErrorLog]

    def content_refs(self) -> set[str]:
        refs: set[str] = set()
        for prefix, items in (
            ("article", self.articles),
            ("paper", self.papers),
            ("course", self.courses),
            ("opportunity", self.opportunities),
            ("tool", self.tools),
        ):
            refs.update(f"{prefix}:{item.slug}" for item in items)
        return refs

    @model_validator(mode="after")
    def _check_references(self) -> Self:
        problems: list[str] = []

        def unique(name: str, keys: list[str]) -> set[str]:
            if len(keys) != len(set(keys)):
                problems.append(f"duplicate {name}")
            return set(keys)

        sources = unique("source slug", [s.slug for s in self.sources])
        categories = unique("category slug", [c.slug for c in self.categories])
        tags = unique("tag slug", [t.slug for t in self.tags])
        authors = unique("author slug", [a.slug for a in self.authors])
        users = unique("user key", [u.key for u in self.users])
        jobs = unique("collection job key", [j.key for j in self.collection_jobs])
        content = self.content_refs()
        courses = {c.slug for c in self.courses}

        def need(kind: str, value: str | None, known: set[str]) -> None:
            if value is not None and value not in known:
                problems.append(f"unknown {kind} {value!r}")

        for c in self.categories:
            need("parent category", c.parent, categories)
        all_content: list[_SeedContent] = [
            *self.articles,
            *self.papers,
            *self.courses,
            *self.opportunities,
            *self.tools,
        ]
        for item in all_content:
            need("category", item.category, categories)
            need("source", item.source, sources)
            for tag in item.tags:
                need("tag", tag, tags)
        authored: list[SeedArticle | SeedPaper] = [*self.articles, *self.papers]
        for with_authors in authored:
            for author in with_authors.authors:
                need("author", author, authors)
        for path in self.learning_paths:
            for step in path.steps:
                need("course", step.course, courses)
        for user in self.users:
            for interest in user.interests:
                need("category", interest.category, categories)
            for ref in user.saved:
                need("content", ref, content)
        for note in self.notifications:
            need("user", note.user, users)
            need("content", note.content, content)
        for brief in self.daily_briefs:
            for brief_item in brief.items:
                need("content", brief_item.content, content)
        for job in self.collection_jobs:
            need("source", job.source, sources)
        for log in self.processing_logs:
            need("content", log.content, content)
            need("collection job", log.collection_job, jobs)
        for err in self.error_logs:
            need("collection job", err.collection_job, jobs)

        if problems:
            raise ValueError("Invalid seed data: " + "; ".join(sorted(set(problems))))
        return self
