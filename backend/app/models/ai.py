"""AI outputs: summaries, classifications and embeddings.

Each output records which model and prompt version produced it and links to
the ``processing_logs`` row of the run, so every AI result is traceable.
Old versions are kept (``is_current = false``) for comparison and rollback.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal
from typing import Any

from pgvector.sqlalchemy import Vector
from sqlalchemy import (
    BigInteger,
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Identity,
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
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin
from app.models.enums import EmbeddingKind, Language, SummaryKind, db_enum

# All embedding models used by NOVA must produce vectors of this size
# (ARCHITECTURE.md §8: Voyage multilingual and bge-m3 are both 1024).
EMBEDDING_DIMENSIONS = 1024


class AISummary(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """An AI-written summary of one item in one language.

    ``sections`` holds the structured parts the Article page shows
    (what happened, metrics, quote, timeline) or a paper analysis.
    """

    __tablename__ = "ai_summaries"
    __table_args__ = (
        # Only ONE current summary per item, kind and language.
        Index(
            "uq_ai_summaries_current",
            "content_id",
            "kind",
            "language",
            unique=True,
            postgresql_where=text("is_current"),
        ),
    )

    content_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("content_items.id", ondelete="CASCADE"), index=True
    )
    kind: Mapped[SummaryKind] = mapped_column(db_enum(SummaryKind, "summary_kind"))
    language: Mapped[Language] = mapped_column(db_enum(Language, "language"))
    is_current: Mapped[bool] = mapped_column(Boolean, server_default=text("true"))
    tldr: Mapped[str | None] = mapped_column(Text)
    key_points: Mapped[list[str]] = mapped_column(JSONB, server_default=text("'[]'::jsonb"))
    why_it_matters: Mapped[str | None] = mapped_column(Text)
    sections: Mapped[dict[str, Any]] = mapped_column(JSONB, server_default=text("'{}'::jsonb"))
    model: Mapped[str | None] = mapped_column(String(100))
    prompt_version: Mapped[str | None] = mapped_column(String(50))
    processing_log_id: Mapped[int | None] = mapped_column(
        ForeignKey("processing_logs.id", ondelete="SET NULL"), index=True
    )
    reviewed_by: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), index=True
    )
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class AIClassification(UUIDPrimaryKeyMixin, Base):
    """What the AI decided about an item: relevant? which category? how important?"""

    __tablename__ = "ai_classifications"
    __table_args__ = (
        CheckConstraint(
            "importance IS NULL OR importance BETWEEN 1 AND 5", name="importance_range"
        ),
        CheckConstraint(
            "confidence IS NULL OR confidence BETWEEN 0 AND 1", name="confidence_range"
        ),
        Index(
            "uq_ai_classifications_current",
            "content_id",
            unique=True,
            postgresql_where=text("is_current"),
        ),
    )

    content_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("content_items.id", ondelete="CASCADE"), index=True
    )
    is_current: Mapped[bool] = mapped_column(Boolean, server_default=text("true"))
    is_relevant: Mapped[bool] = mapped_column(Boolean)
    suggested_category_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("categories.id", ondelete="SET NULL"), index=True
    )
    importance: Mapped[int | None] = mapped_column(SmallInteger)
    confidence: Mapped[Decimal | None] = mapped_column(Numeric(4, 3))
    # e.g. {"topics": [{"slug": "ai-agents", "score": 0.91}], "reasons": "..."}
    labels: Mapped[dict[str, Any]] = mapped_column(JSONB, server_default=text("'{}'::jsonb"))
    model: Mapped[str | None] = mapped_column(String(100))
    prompt_version: Mapped[str | None] = mapped_column(String(50))
    processing_log_id: Mapped[int | None] = mapped_column(
        ForeignKey("processing_logs.id", ondelete="SET NULL"), index=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=text("now()")
    )


class Embedding(Base):
    """A vector representing the meaning of an item (or one passage of it).

    Used for semantic search, related content and RAG (Phases 8-9).
    """

    __tablename__ = "embeddings"
    __table_args__ = (
        UniqueConstraint(
            "content_id", "model", "kind", "chunk_index", name="uq_embeddings_content_chunk"
        ),
        CheckConstraint("chunk_index >= 0", name="chunk_index_nonneg"),
        CheckConstraint("kind = 'chunk' OR chunk_index = 0", name="document_single_row"),
        # Approximate nearest-neighbour index for cosine similarity.
        Index(
            "ix_embeddings_vector_hnsw",
            "embedding",
            postgresql_using="hnsw",
            postgresql_ops={"embedding": "vector_cosine_ops"},
        ),
    )

    id: Mapped[int] = mapped_column(BigInteger, Identity(), primary_key=True)
    content_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("content_items.id", ondelete="CASCADE"), index=True
    )
    kind: Mapped[EmbeddingKind] = mapped_column(db_enum(EmbeddingKind, "embedding_kind"))
    chunk_index: Mapped[int] = mapped_column(Integer, server_default="0")
    language: Mapped[Language | None] = mapped_column(db_enum(Language, "language"))
    chunk_text: Mapped[str | None] = mapped_column(Text)
    token_count: Mapped[int | None] = mapped_column(Integer)
    model: Mapped[str] = mapped_column(String(100))
    embedding: Mapped[list[float]] = mapped_column(Vector(EMBEDDING_DIMENSIONS))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=text("now()")
    )
