"""Queries for content items (articles, papers, courses, opportunities, tools)."""

from __future__ import annotations

from collections.abc import Sequence

from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.models import ContentItem
from app.models.enums import ContentStatus, ContentType
from app.repositories.base import MAX_PAGE_SIZE, BaseRepository

_DETAILS = (
    selectinload(ContentItem.article),
    selectinload(ContentItem.paper),
    selectinload(ContentItem.course),
    selectinload(ContentItem.opportunity),
    selectinload(ContentItem.tool),
    selectinload(ContentItem.category),
    selectinload(ContentItem.source),
)


class ContentRepository(BaseRepository[ContentItem]):
    model = ContentItem

    async def get_by_slug(self, content_type: ContentType, slug: str) -> ContentItem | None:
        """One item with its type-specific details, category and source loaded."""
        stmt = (
            select(ContentItem)
            .where(ContentItem.content_type == content_type, ContentItem.slug == slug)
            .options(*_DETAILS)
        )
        result: ContentItem | None = await self.session.scalar(stmt)
        return result

    async def list_published(
        self, content_type: ContentType, *, limit: int = 20, offset: int = 0
    ) -> Sequence[ContentItem]:
        """Published items of one type, newest first (uses ix_content_items_listing)."""
        if not 1 <= limit <= MAX_PAGE_SIZE:
            raise ValueError(f"limit must be between 1 and {MAX_PAGE_SIZE}")
        stmt = (
            select(ContentItem)
            .where(
                ContentItem.content_type == content_type,
                ContentItem.status == ContentStatus.PUBLISHED,
            )
            .order_by(ContentItem.published_at.desc().nulls_last(), ContentItem.id)
            .limit(limit)
            .offset(offset)
            .options(*_DETAILS)
        )
        return (await self.session.scalars(stmt)).all()
