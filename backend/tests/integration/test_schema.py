"""The real database enforces the rules described in DATABASE.md (needs TEST_DATABASE_URL)."""

from __future__ import annotations

import asyncio
import uuid
from collections.abc import AsyncIterator
from datetime import UTC, datetime

import pytest
from sqlalchemy import func, select, text
from sqlalchemy.exc import DBAPIError, IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import Database
from app.models import (
    AISummary,
    Article,
    Category,
    ContentItem,
    Embedding,
    ErrorLog,
    Notification,
    ProcessingLog,
    SavedItem,
    User,
    UserInterest,
    UserPreferences,
)
from app.models.enums import (
    ContentStatus,
    ContentType,
    EmbeddingKind,
    Language,
    NotificationKind,
    ProcessingStep,
    StepStatus,
    SummaryKind,
)
from app.repositories import ContentRepository, ErrorLogRepository
from tests.unit.test_models import EXPECTED_TABLES

pytestmark = pytest.mark.db


@pytest.fixture
async def session(database: Database) -> AsyncIterator[AsyncSession]:
    """A session whose changes are always rolled back, so tests don't affect each other."""
    async with database.session() as s:
        yield s
        await s.rollback()


def _article(slug: str = "test-article", **overrides: object) -> ContentItem:
    values: dict[str, object] = {
        "content_type": ContentType.ARTICLE,
        "slug": slug,
        "status": ContentStatus.PUBLISHED,
        "title_en": f"Title {slug}",
        "published_at": datetime.now(UTC),
    }
    values.update(overrides)
    return ContentItem(**values)


# --- Structure --------------------------------------------------------------------------


async def test_all_tables_exist(session: AsyncSession) -> None:
    rows = await session.scalars(text("SELECT tablename FROM pg_tables WHERE schemaname = 'app'"))
    assert set(rows.all()) - {"alembic_version"} == EXPECTED_TABLES


async def test_row_level_security_enabled_everywhere(session: AsyncSession) -> None:
    rows = await session.scalars(
        text(
            "SELECT tablename FROM pg_tables WHERE schemaname = 'app' "
            "AND tablename <> 'alembic_version' AND NOT rowsecurity"
        )
    )
    assert rows.all() == []


async def test_updated_at_trigger_on_every_table_with_updated_at(session: AsyncSession) -> None:
    rows = await session.scalars(
        text(
            """
            SELECT c.table_name FROM information_schema.columns c
            WHERE c.table_schema = 'app' AND c.column_name = 'updated_at'
              AND NOT EXISTS (
                SELECT 1 FROM information_schema.triggers t
                WHERE t.event_object_schema = 'app' AND t.event_object_table = c.table_name
                  AND t.action_statement LIKE '%set_updated_at%'
              )
            """
        )
    )
    assert rows.all() == []


async def test_extensions_installed(session: AsyncSession) -> None:
    names = await session.scalars(
        text("SELECT extname FROM pg_extension WHERE extname IN ('vector', 'pg_trgm')")
    )
    assert set(names.all()) == {"vector", "pg_trgm"}


# --- Constraints -----------------------------------------------------------------------


async def test_slug_unique_per_content_type(session: AsyncSession) -> None:
    session.add(_article("same-slug"))
    await session.flush()
    # Same slug for a different content type is fine…
    session.add(ContentItem(content_type=ContentType.COURSE, slug="same-slug", title_en="A course"))
    await session.flush()
    # …but not twice for the same type.
    with pytest.raises(IntegrityError):
        async with session.begin_nested():
            session.add(_article("same-slug"))
            await session.flush()


@pytest.mark.parametrize(
    ("statement", "rule"),
    [
        (  # invalid "enum" value
            "INSERT INTO app.content_items (content_type, slug, title_en) "
            "VALUES ('video', 'x', 'X')",
            "ck_content_items_content_type",
        ),
        (  # importance must be 1-5
            "INSERT INTO app.content_items (content_type, slug, title_en, importance) "
            "VALUES ('article', 'x', 'X', 6)",
            "ck_content_items_importance_range",
        ),
        (  # an item needs a title in at least one language
            "INSERT INTO app.content_items (content_type, slug) VALUES ('article', 'x')",
            "ck_content_items_has_title",
        ),
        (  # source trust level must be 1-5
            "INSERT INTO app.sources (slug, name, kind, trust_level) VALUES ('s', 'S', 'rss', 9)",
            "ck_sources_trust_level_range",
        ),
        (  # foreign key: category must exist
            "INSERT INTO app.content_items (content_type, slug, title_en, category_id) "
            "VALUES ('article', 'x', 'X', gen_random_uuid())",
            "fk_content_items_category_id_categories",
        ),
    ],
)
async def test_invalid_rows_rejected(session: AsyncSession, statement: str, rule: str) -> None:
    with pytest.raises(IntegrityError) as excinfo:
        async with session.begin_nested():
            await session.execute(text(statement))
    assert rule in str(excinfo.value)


async def test_only_one_current_summary_per_language(session: AsyncSession) -> None:
    item = _article()
    session.add(item)
    await session.flush()
    for current in (False, True):
        session.add(
            AISummary(
                content_id=item.id,
                kind=SummaryKind.ARTICLE_BRIEF,
                language=Language.EN,
                is_current=current,
                tldr="v1",
            )
        )
    await session.flush()
    with pytest.raises(IntegrityError):
        async with session.begin_nested():
            session.add(
                AISummary(
                    content_id=item.id,
                    kind=SummaryKind.ARTICLE_BRIEF,
                    language=Language.EN,
                    tldr="v2",
                )
            )
            await session.flush()


async def test_user_email_unique_ignoring_case(session: AsyncSession) -> None:
    session.add(User(id=uuid.uuid4(), email="Someone@Example.com"))
    await session.flush()
    with pytest.raises(IntegrityError):
        async with session.begin_nested():
            session.add(User(id=uuid.uuid4(), email="someone@example.com"))
            await session.flush()


# --- Relationships & deletes -----------------------------------------------------------


async def test_deleting_content_cleans_up_dependents(session: AsyncSession) -> None:
    user = User(id=uuid.uuid4(), email="cascade@example.com")
    item = _article()
    session.add_all([user, item])
    await session.flush()
    session.add_all(
        [
            Article(content_id=item.id, reading_minutes=3),
            SavedItem(user_id=user.id, content_id=item.id),
            AISummary(
                content_id=item.id, kind=SummaryKind.ARTICLE_BRIEF, language=Language.EN, tldr="t"
            ),
            Embedding(
                content_id=item.id,
                kind=EmbeddingKind.DOCUMENT,
                model="test",
                embedding=[0.1] * 1024,
            ),
            Notification(
                user_id=user.id, kind=NotificationKind.SYSTEM, title_en="n", content_id=item.id
            ),
            ProcessingLog(
                content_id=item.id, step=ProcessingStep.SUMMARIZE, status=StepStatus.SUCCEEDED
            ),
        ]
    )
    await session.flush()

    await session.execute(text("DELETE FROM app.content_items WHERE id = :id"), {"id": item.id})

    async def count(sql: str) -> int:
        return int(await session.scalar(text(sql), {"id": item.id}) or 0)

    # Owned data is removed …
    for table in ("articles", "saved_items", "ai_summaries", "embeddings"):
        assert await count(f"SELECT count(*) FROM app.{table} WHERE content_id = :id") == 0  # noqa: S608
    # … history and notifications are kept, just unlinked.
    assert await count("SELECT count(*) FROM app.notifications WHERE user_id IS NOT NULL "
                       "AND title_en = 'n' AND content_id IS NULL") == 1  # fmt: skip
    assert await count("SELECT count(*) FROM app.processing_logs WHERE content_id = :id") == 0


async def test_deleting_user_removes_personal_data(session: AsyncSession) -> None:
    category = Category(slug="test-cat", name_en="Test", name_ar="اختبار")
    user = User(id=uuid.uuid4(), email="gone@example.com")
    item = _article()
    session.add_all([category, user, item])
    await session.flush()
    session.add_all(
        [
            UserPreferences(user_id=user.id),
            UserInterest(user_id=user.id, category_id=category.id),
            SavedItem(user_id=user.id, content_id=item.id),
            Notification(user_id=user.id, kind=NotificationKind.SYSTEM, title_en="hi"),
        ]
    )
    await session.flush()
    await session.execute(text("DELETE FROM app.users WHERE id = :id"), {"id": user.id})
    for table in ("user_preferences", "user_interests", "saved_items", "notifications"):
        remaining = await session.scalar(
            text(f"SELECT count(*) FROM app.{table} WHERE user_id = :id"),  # noqa: S608
            {"id": user.id},
        )
        assert remaining == 0, table
    # The content itself is untouched.
    assert await session.get(ContentItem, item.id) is not None


async def test_deleting_category_keeps_content(session: AsyncSession) -> None:
    category = Category(slug="temp-cat", name_en="Temp", name_ar="مؤقت")
    session.add(category)
    await session.flush()
    item = _article(category_id=category.id)
    session.add(item)
    await session.flush()
    await session.execute(text("DELETE FROM app.categories WHERE id = :id"), {"id": category.id})
    category_id = await session.scalar(
        select(ContentItem.category_id).where(ContentItem.id == item.id)
    )
    assert category_id is None


# --- Timestamps --------------------------------------------------------------------------


async def test_updated_at_changes_on_update(database: Database) -> None:
    slug = f"ts-{uuid.uuid4().hex[:8]}"
    async with database.session() as s:
        item = _article(slug)
        s.add(item)
        await s.commit()
        created = item.updated_at
    await asyncio.sleep(0.01)
    try:
        async with database.session() as s:
            await s.execute(
                text("UPDATE app.content_items SET title_en = 'changed' WHERE slug = :slug"),
                {"slug": slug},
            )
            await s.commit()
            updated = await s.scalar(
                text("SELECT updated_at FROM app.content_items WHERE slug = :slug"),
                {"slug": slug},
            )
        assert updated is not None and updated > created
    finally:
        async with database.session() as s:
            await s.execute(
                text("DELETE FROM app.content_items WHERE slug = :slug"), {"slug": slug}
            )
            await s.commit()


# --- Search helpers --------------------------------------------------------------------


async def test_embedding_similarity_search(session: AsyncSession) -> None:
    def vector(first: float, second: float) -> list[float]:
        return [first, second] + [0.0] * 1022

    items = {name: _article(name) for name in ("north", "east", "north-ish")}
    session.add_all(items.values())
    await session.flush()
    for name, vec in (
        ("north", vector(1, 0)),
        ("east", vector(0, 1)),
        ("north-ish", vector(0.9, 0.1)),
    ):
        session.add(
            Embedding(
                content_id=items[name].id, kind=EmbeddingKind.DOCUMENT, model="test", embedding=vec
            )
        )
    await session.flush()

    query = vector(1, 0.05)
    distance = Embedding.embedding.cosine_distance(query)
    rows = await session.execute(
        select(ContentItem.slug)
        .join(Embedding, Embedding.content_id == ContentItem.id)
        .where(Embedding.model == "test")
        .order_by(distance)
    )
    assert [r.slug for r in rows] == ["north", "north-ish", "east"]


async def test_embedding_dimension_enforced(session: AsyncSession) -> None:
    item = _article()
    session.add(item)
    await session.flush()
    with pytest.raises(DBAPIError):
        async with session.begin_nested():
            session.add(
                Embedding(
                    content_id=item.id, kind=EmbeddingKind.DOCUMENT, model="t", embedding=[1.0] * 3
                )
            )
            await session.flush()


async def test_fuzzy_title_search(session: AsyncSession) -> None:
    session.add(_article("fuzzy", title_en="Multimodal reasoning breakthrough"))
    await session.flush()
    similarity = func.similarity(ContentItem.title_en, "multimodl reasonin")  # typos
    best = await session.scalar(
        select(ContentItem.slug).where(similarity > 0.3).order_by(similarity.desc()).limit(1)
    )
    assert best == "fuzzy"


# --- Repositories ------------------------------------------------------------------------


async def test_content_repository_loads_details(session: AsyncSession) -> None:
    item = _article("with-details")
    session.add(item)
    await session.flush()
    session.add(Article(content_id=item.id, reading_minutes=4))
    await session.flush()
    session.expunge_all()

    found = await ContentRepository(session).get_by_slug(ContentType.ARTICLE, "with-details")
    assert found is not None and found.article is not None
    assert found.article.reading_minutes == 4
    listed = await ContentRepository(session).list_published(ContentType.ARTICLE, limit=100)
    assert "with-details" in {i.slug for i in listed}


async def test_error_log_repository_redacts_secrets(session: AsyncSession) -> None:
    try:
        raise ConnectionError("cannot reach postgresql://nova:hunter2@db.example.com/nova")
    except ConnectionError as exc:
        entry = await ErrorLogRepository(session).record(
            exc,
            component="collector",
            context={"api_key": "sk-live-123", "url": "https://u:pw@example.com/feed"},
        )
    stored = await session.get(ErrorLog, entry.id)
    assert stored is not None
    everything = f"{stored.message} {stored.stack_trace} {stored.context}"
    for secret in ("hunter2", "sk-live-123", ":pw@"):
        assert secret not in everything
    assert stored.error_type == "ConnectionError"
