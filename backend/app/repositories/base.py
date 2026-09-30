"""Generic repository: the only layer that talks to the database directly.

Layering rule used throughout the backend::

    API route  ->  service (business rules)  ->  repository (queries)  ->  database

Repositories never commit; the service that owns the unit of work does.
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any, ClassVar

from sqlalchemy import ScalarResult, func, inspect, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import DeclarativeBase

MAX_PAGE_SIZE = 100


class BaseRepository[ModelT: DeclarativeBase]:
    """Common CRUD helpers. Subclasses set ``model``::

    class ArticleRepository(BaseRepository[Article]):
        model = Article
    """

    model: ClassVar[type[Any]]

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get(self, id_: Any) -> ModelT | None:
        result: ModelT | None = await self.session.get(self.model, id_)
        return result

    async def get_many(self, *, limit: int = 20, offset: int = 0) -> Sequence[ModelT]:
        if not 1 <= limit <= MAX_PAGE_SIZE:
            raise ValueError(f"limit must be between 1 and {MAX_PAGE_SIZE}")
        if offset < 0:
            raise ValueError("offset must not be negative")
        primary_key = inspect(self.model).primary_key
        stmt = select(self.model).order_by(*primary_key).limit(limit).offset(offset)
        result: ScalarResult[ModelT] = await self.session.scalars(stmt)
        return result.all()

    async def count(self) -> int:
        total = await self.session.scalar(select(func.count()).select_from(self.model))
        return int(total or 0)

    async def add(self, instance: ModelT) -> ModelT:
        self.session.add(instance)
        await self.session.flush()
        return instance

    async def delete(self, instance: ModelT) -> None:
        await self.session.delete(instance)
        await self.session.flush()
