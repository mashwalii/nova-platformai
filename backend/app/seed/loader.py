"""Load the development seed data into the database.

* Idempotent: every row gets a fixed id derived from its natural key
  (``uuid5``), and rows are inserted with "insert or update". Running the seed
  twice leaves exactly one copy of everything.
* Development/test only: the CLI refuses to run it in staging/production.
"""

from __future__ import annotations

import json
import uuid
from collections import Counter
from collections.abc import Sequence
from pathlib import Path
from typing import Any, cast

from sqlalchemy import Table, delete
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import (
    AIClassification,
    AISummary,
    AITool,
    Article,
    Author,
    Base,
    Category,
    CollectionJob,
    ContentAuthor,
    ContentItem,
    ContentTag,
    Course,
    DailyBrief,
    DailyBriefItem,
    ErrorLog,
    LearningPath,
    LearningPathStep,
    Notification,
    Opportunity,
    Paper,
    ProcessingLog,
    SavedItem,
    Source,
    Tag,
    User,
    UserInterest,
    UserPreferences,
)
from app.models.enums import (
    ContentStatus,
    ContentType,
    Language,
    SummaryKind,
    TagOrigin,
)
from app.seed.schema import Localized, SeedData, _SeedContent

DEV_SEED_FILE = Path(__file__).parent / "data" / "dev_seed.json"
SEED_NAMESPACE = uuid.UUID("7d3f5f5e-4c1a-4f0e-9a51-6c7a2b1e0d42")
SEED_MARKER = {"seed": "dev"}
SAMPLE_MODEL = "sample (hand-written)"

__all__ = ["DEV_SEED_FILE", "load_seed", "read_seed_file", "seed_id"]


def seed_id(kind: str, key: str) -> uuid.UUID:
    """Stable id for a seed row, e.g. seed_id("content", "article:benchmark")."""
    return uuid.uuid5(SEED_NAMESPACE, f"{kind}:{key}")


def read_seed_file(path: Path = DEV_SEED_FILE) -> SeedData:
    return SeedData.model_validate(json.loads(path.read_text(encoding="utf-8")))


def _en(value: Localized | None) -> str | None:
    return value.en if value else None


def _ar(value: Localized | None) -> str | None:
    return value.ar if value else None


async def _upsert(session: AsyncSession, model: type[Base], rows: Sequence[dict[str, Any]]) -> int:
    """Insert rows, or update them if a row with the same primary key exists."""
    if not rows:
        return 0
    table = cast(Table, model.__table__)
    primary_key = [column.name for column in table.primary_key.columns]
    statement = pg_insert(table).values(list(rows))
    updates = {
        name: statement.excluded[name]
        for name in rows[0]
        if name not in primary_key and name != "created_at"
    }
    statement = (
        statement.on_conflict_do_update(index_elements=primary_key, set_=updates)
        if updates
        else statement.on_conflict_do_nothing(index_elements=primary_key)
    )
    await session.execute(statement)
    return len(rows)


def _content_row(content_type: ContentType, item: _SeedContent) -> dict[str, Any]:
    ref = f"{content_type.value}:{item.slug}"
    return {
        "id": seed_id("content", ref),
        "content_type": content_type,
        "slug": item.slug,
        "status": ContentStatus.PUBLISHED,
        "source_id": seed_id("source", item.source),
        "category_id": seed_id("category", item.category) if item.category else None,
        "original_language": Language.EN,
        "title_en": item.title.en,
        "title_ar": item.title.ar,
        "summary_en": _en(item.summary),
        "summary_ar": _ar(item.summary),
        "canonical_url": item.canonical_url,
        "published_at": item.published_at,
        "source_updated_at": None,
        "importance": item.importance,
        "is_featured": item.is_featured,
        "is_trending": False,
        "view_count": 0,
        "extra": {**item.extra, **SEED_MARKER},
    }


def _content_id(ref: str) -> uuid.UUID:
    return seed_id("content", ref)


async def load_seed(session: AsyncSession, data: SeedData) -> dict[str, int]:
    """Write ``data`` to the database (caller commits). Returns rows per table."""
    counts: Counter[str] = Counter()

    async def put(model: type[Base], rows: Sequence[dict[str, Any]]) -> None:
        counts[str(model.__tablename__)] += await _upsert(session, model, rows)

    # --- reference data ----------------------------------------------------------
    await put(
        Source,
        [
            {
                "id": seed_id("source", s.slug),
                "slug": s.slug,
                "name": s.name,
                "kind": s.kind,
                "homepage_url": s.homepage_url,
                "feed_url": s.feed_url,
                "language": s.language,
                "trust_level": s.trust_level,
                "is_active": s.is_active,
                "fetch_interval_minutes": s.fetch_interval_minutes,
                "config": s.config,
            }
            for s in data.sources
        ],
    )
    await put(
        Category,
        [
            {
                "id": seed_id("category", c.slug),
                "slug": c.slug,
                "name_en": c.name.en,
                "name_ar": c.name.ar,
                "parent_id": seed_id("category", c.parent) if c.parent else None,
                "content_type": c.content_type,
                "sort_order": c.sort_order,
            }
            for c in data.categories
        ],
    )
    await put(
        Tag,
        [
            {
                "id": seed_id("tag", t.slug),
                "slug": t.slug,
                "name_en": t.name.en,
                "name_ar": t.name.ar,
            }
            for t in data.tags
        ],
    )
    await put(
        Author,
        [
            {
                "id": seed_id("author", a.slug),
                "slug": a.slug,
                "name": a.name,
                "name_ar": a.name_ar,
                "affiliation": a.affiliation,
            }
            for a in data.authors
        ],
    )

    # --- content ---------------------------------------------------------------------
    content_rows: list[dict[str, Any]] = []
    for article in data.articles:
        row = _content_row(ContentType.ARTICLE, article)
        row.update(
            source_updated_at=article.source_updated_at,
            view_count=article.view_count,
            is_trending=article.is_trending,
        )
        content_rows.append(row)
    content_rows += [_content_row(ContentType.PAPER, p) for p in data.papers]
    content_rows += [_content_row(ContentType.COURSE, c) for c in data.courses]
    content_rows += [_content_row(ContentType.OPPORTUNITY, o) for o in data.opportunities]
    content_rows += [_content_row(ContentType.TOOL, t) for t in data.tools]
    await put(ContentItem, content_rows)

    await put(
        Article,
        [
            {
                "content_id": _content_id(f"article:{a.slug}"),
                "reading_minutes": a.reading_minutes,
            }
            for a in data.articles
        ],
    )
    await put(
        Paper,
        [
            {
                "content_id": _content_id(f"paper:{p.slug}"),
                "arxiv_id": p.arxiv_id,
                "abstract": None,  # not copied: summaries are written by NOVA
                "subject_areas": p.subject_areas,
                "pdf_url": p.pdf_url,
                "venue": p.venue,
            }
            for p in data.papers
        ],
    )
    await put(
        Course,
        [
            {
                "content_id": _content_id(f"course:{c.slug}"),
                "provider": c.provider,
                "level": c.level,
                "duration_label_en": _en(c.duration_label),
                "duration_label_ar": _ar(c.duration_label),
                "instruction_language_en": _en(c.instruction_language),
                "instruction_language_ar": _ar(c.instruction_language),
                "is_free": c.is_free,
                "enrollment_url": c.enrollment_url,
            }
            for c in data.courses
        ],
    )
    await put(
        Opportunity,
        [
            {
                "content_id": _content_id(f"opportunity:{o.slug}"),
                "opportunity_type": o.opportunity_type,
                "organization": o.organization,
                "location_en": _en(o.location),
                "location_ar": _ar(o.location),
                "country_code": o.country_code,
                "is_remote": o.is_remote,
                "eligibility_en": _en(o.eligibility),
                "eligibility_ar": _ar(o.eligibility),
                "deadline_at": o.deadline_at,
                "apply_url": o.canonical_url,
                "employment_type": o.employment_type,
                "seniority": o.seniority,
                "salary_text": o.salary_text,
            }
            for o in data.opportunities
        ],
    )
    await put(
        AITool,
        [
            {
                "content_id": _content_id(f"tool:{t.slug}"),
                "website_url": t.website_url,
                "pricing": t.pricing,
                "vendor": t.vendor,
                "platforms": t.platforms,
                "has_api": t.has_api,
                "repository_url": t.repository_url,
            }
            for t in data.tools
        ],
    )
    await put(
        LearningPath,
        [
            {
                "id": seed_id("path", p.slug),
                "slug": p.slug,
                "title_en": p.title.en,
                "title_ar": p.title.ar,
                "level": p.level,
                "sort_order": index,
            }
            for index, p in enumerate(data.learning_paths)
        ],
    )
    await put(
        LearningPathStep,
        [
            {
                "id": seed_id("path-step", f"{p.slug}:{position}"),
                "path_id": seed_id("path", p.slug),
                "position": position,
                "title_en": step.title.en,
                "title_ar": step.title.ar,
                "course_id": _content_id(f"course:{step.course}") if step.course else None,
            }
            for p in data.learning_paths
            for position, step in enumerate(p.steps, start=1)
        ],
    )

    # --- links: authors & tags ------------------------------------------------------
    author_rows = [
        {
            "content_id": _content_id(f"{kind}:{item.slug}"),
            "author_id": seed_id("author", author),
            "position": position,
        }
        for kind, items in (("article", data.articles), ("paper", data.papers))
        for item in items
        for position, author in enumerate(item.authors, start=1)
    ]
    await put(ContentAuthor, author_rows)
    tag_rows = [
        {
            "content_id": _content_id(f"{kind}:{item.slug}"),
            "tag_id": seed_id("tag", tag),
            "origin": TagOrigin.EDITOR,
        }
        for kind, items in (
            ("article", data.articles),
            ("paper", data.papers),
            ("tool", data.tools),
        )
        for item in items
        for tag in item.tags
    ]
    await put(ContentTag, tag_rows)

    # --- AI outputs (hand-written samples standing in for real AI results) -----------
    await put(
        AISummary,
        [
            {
                "id": seed_id("summary", f"article:{a.slug}:{lang.value}"),
                "content_id": _content_id(f"article:{a.slug}"),
                "kind": SummaryKind.ARTICLE_BRIEF,
                "language": lang,
                "is_current": True,
                "tldr": brief.tldr,
                "key_points": brief.key_points,
                "why_it_matters": brief.why_it_matters,
                "sections": brief.sections,
                "model": SAMPLE_MODEL,
            }
            for a in data.articles
            for lang, brief in a.brief.items()
        ],
    )
    await put(
        AIClassification,
        [
            {
                "id": seed_id("classification", f"article:{a.slug}"),
                "content_id": _content_id(f"article:{a.slug}"),
                "is_current": True,
                "is_relevant": True,
                "suggested_category_id": seed_id("category", a.category) if a.category else None,
                "importance": a.importance,
                "confidence": 0.9,
                "labels": {"topics": a.tags},
                "model": SAMPLE_MODEL,
            }
            for a in data.articles
        ],
    )

    # --- users -------------------------------------------------------------------------
    await put(
        User,
        [
            {
                "id": seed_id("user", u.key),
                "email": u.email,
                "display_name": u.display_name,
                "role": u.role,
            }
            for u in data.users
        ],
    )
    await put(
        UserPreferences,
        [
            {
                "user_id": seed_id("user", u.key),
                "language": u.preferences.language,
                "theme": u.preferences.theme,
                "timezone": u.preferences.timezone,
                "email_digest": u.preferences.email_digest,
            }
            for u in data.users
        ],
    )
    await put(
        UserInterest,
        [
            {
                "user_id": seed_id("user", u.key),
                "category_id": seed_id("category", i.category),
                "weight": i.weight,
            }
            for u in data.users
            for i in u.interests
        ],
    )
    await put(
        SavedItem,
        [
            {"user_id": seed_id("user", u.key), "content_id": _content_id(ref)}
            for u in data.users
            for ref in u.saved
        ],
    )
    await put(
        Notification,
        [
            {
                "id": seed_id("notification", f"{n.user}:{index}"),
                "user_id": seed_id("user", n.user),
                "kind": n.kind,
                "content_id": _content_id(n.content) if n.content else None,
                "title_en": n.title.en,
                "title_ar": n.title.ar,
                "link_path": n.link_path,
                "created_at": n.created_at,
                "read_at": n.read_at,
            }
            for index, n in enumerate(data.notifications)
        ],
    )

    # --- daily briefs -------------------------------------------------------------------
    await put(
        DailyBrief,
        [
            {
                "id": seed_id("brief", b.date.isoformat()),
                "brief_date": b.date,
                "status": b.status,
                "headline_en": b.headline.en,
                "headline_ar": b.headline.ar,
                "intro_en": b.intro.en,
                "intro_ar": b.intro.ar,
                "signal_en": b.signal.en,
                "signal_ar": b.signal.ar,
                "published_at": b.published_at,
                "model": SAMPLE_MODEL,
            }
            for b in data.daily_briefs
        ],
    )
    await put(
        DailyBriefItem,
        [
            {
                "id": seed_id("brief-item", f"{b.date.isoformat()}:{position}"),
                "brief_id": seed_id("brief", b.date.isoformat()),
                "content_id": _content_id(item.content),
                "position": position,
                "blurb_en": item.blurb.en,
                "blurb_ar": item.blurb.ar,
            }
            for b in data.daily_briefs
            for position, item in enumerate(b.items, start=1)
        ],
    )

    # --- operations ----------------------------------------------------------------------
    await put(
        CollectionJob,
        [
            {
                "id": seed_id("job", j.key),
                "job_type": j.job_type,
                "source_id": seed_id("source", j.source) if j.source else None,
                "status": j.status,
                "trigger": j.trigger,
                "started_at": j.started_at,
                "finished_at": j.finished_at,
                "items_found": j.items_found,
                "items_created": j.items_created,
                "items_updated": j.items_updated,
                "items_failed": j.items_failed,
                "error_message": j.error_message,
                "details": {**j.details, **SEED_MARKER},
            }
            for j in data.collection_jobs
        ],
    )
    # Log tables use auto-numbered ids, so previous seed rows are replaced.
    await session.execute(
        delete(ProcessingLog).where(ProcessingLog.details["seed"].astext == "dev")
    )
    await session.execute(delete(ErrorLog).where(ErrorLog.context["seed"].astext == "dev"))
    if data.processing_logs:
        session.add_all(
            ProcessingLog(
                content_id=_content_id(log.content) if log.content else None,
                collection_job_id=seed_id("job", log.collection_job)
                if log.collection_job
                else None,
                step=log.step,
                status=log.status,
                provider=log.provider,
                model=log.model,
                duration_ms=log.duration_ms,
                details=dict(SEED_MARKER),
            )
            for log in data.processing_logs
        )
        counts["processing_logs"] += len(data.processing_logs)
    if data.error_logs:
        session.add_all(
            ErrorLog(
                severity=err.severity,
                component=err.component,
                error_type=err.error_type,
                message=err.message,
                collection_job_id=seed_id("job", err.collection_job)
                if err.collection_job
                else None,
                occurred_at=err.occurred_at,
                resolved_at=err.resolved_at,
                context=dict(SEED_MARKER),
            )
            for err in data.error_logs
        )
        counts["error_logs"] += len(data.error_logs)
    await session.flush()
    return dict(counts)
