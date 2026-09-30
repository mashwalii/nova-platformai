"""The development seed loads correctly and can be re-run (needs TEST_DATABASE_URL)."""

from __future__ import annotations

from collections.abc import AsyncIterator

import pytest
from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import Database
from app.models import (
    AISummary,
    Category,
    ContentItem,
    DailyBriefItem,
    Opportunity,
    SavedItem,
    User,
)
from app.models.enums import ContentType, Language, OpportunityType
from app.repositories import ContentRepository
from app.seed import load_seed, read_seed_file, seed_id

pytestmark = pytest.mark.db

SEEDED_TABLES = (
    "sources", "categories", "tags", "authors", "content_items", "articles", "papers",
    "courses", "opportunities", "ai_tools", "learning_paths", "learning_path_steps",
    "content_authors", "content_tags", "ai_summaries", "ai_classifications", "users",
    "user_preferences", "user_interests", "saved_items", "notifications", "daily_briefs",
    "daily_brief_items", "collection_jobs", "processing_logs", "error_logs",
)  # fmt: skip


@pytest.fixture
async def seeded(database: Database) -> AsyncIterator[Database]:
    """Load the seed (the whole test database is rebuilt at the start of each run)."""
    async with database.session() as session:
        await load_seed(session, read_seed_file())
        await session.commit()
    yield database


async def _counts(session: AsyncSession) -> dict[str, int]:
    return {
        table: int(await session.scalar(text(f"SELECT count(*) FROM app.{table}")) or 0)  # noqa: S608
        for table in SEEDED_TABLES
    }


async def test_seed_is_idempotent(seeded: Database) -> None:
    async with seeded.session() as session:
        first = await _counts(session)
        await load_seed(session, read_seed_file())
        await session.commit()
        second = await _counts(session)
    assert first == second
    assert all(first[table] > 0 for table in SEEDED_TABLES), first


async def test_seed_matches_file(seeded: Database) -> None:
    data = read_seed_file()
    async with seeded.session() as session:
        total = await session.scalar(select(func.count()).select_from(ContentItem))
        assert total is not None and total >= len(data.content_refs())
        types = (await session.scalars(select(Opportunity.opportunity_type).distinct())).all()
        assert set(types) == set(OpportunityType)


async def test_seeded_article_has_everything_the_article_page_needs(seeded: Database) -> None:
    async with seeded.session() as session:
        article = await ContentRepository(session).get_by_slug(
            ContentType.ARTICLE, "multimodal-reasoning"
        )
        assert article is not None
        assert article.title_ar and article.summary_en
        assert article.article is not None and article.article.reading_minutes == 6
        assert article.category is not None and article.category.slug == "ai-research"
        assert article.source is not None and article.source.name == "NOVA Intelligence"
        assert article.is_featured and article.importance == 5

        summaries = (
            await session.scalars(
                select(AISummary).where(AISummary.content_id == article.id, AISummary.is_current)
            )
        ).all()
        assert {s.language for s in summaries} == {Language.EN, Language.AR}
        english = next(s for s in summaries if s.language == Language.EN)
        assert len(english.key_points) == 3
        assert set(english.sections) == {"what_happened", "metrics", "quote", "timeline"}


async def test_seeded_users_and_relationships(seeded: Database) -> None:
    async with seeded.session() as session:
        reader = await session.get(User, seed_id("user", "reader"))
        assert reader is not None and reader.email == "reader@example.com"
        saved = await session.scalar(
            select(func.count()).select_from(SavedItem).where(SavedItem.user_id == reader.id)
        )
        assert saved == 3
        course_categories = await session.scalar(
            select(func.count()).select_from(Category).where(Category.content_type == "course")
        )
        assert course_categories == 8
        brief_items = await session.scalar(select(func.count()).select_from(DailyBriefItem))
        assert brief_items is not None and brief_items >= 3
