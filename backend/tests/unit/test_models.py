"""Structural rules every table must follow (checked without a database)."""

from __future__ import annotations

import pytest
from sqlalchemy import Table

from app.models import APP_SCHEMA, EMBEDDING_DIMENSIONS, Base

TABLES: list[Table] = sorted(Base.metadata.tables.values(), key=lambda t: t.name)

EXPECTED_TABLES = {
    # reference data
    "sources", "authors", "categories", "tags",
    # content
    "content_items", "articles", "papers", "courses", "opportunities", "ai_tools",
    "learning_paths", "learning_path_steps", "content_authors", "content_tags",
    # AI
    "ai_summaries", "ai_classifications", "embeddings",
    # users
    "users", "user_preferences", "user_interests", "saved_items", "notifications",
    # briefs
    "daily_briefs", "daily_brief_items",
    # operations
    "collection_jobs", "processing_logs", "error_logs",
}  # fmt: skip


def test_expected_tables_exist() -> None:
    assert {t.name for t in TABLES} == EXPECTED_TABLES


@pytest.mark.parametrize("table", TABLES, ids=lambda t: t.name)
def test_table_is_in_app_schema_with_primary_key(table: Table) -> None:
    assert table.schema == APP_SCHEMA
    assert table.primary_key.columns, f"{table.name} has no primary key"


@pytest.mark.parametrize("table", TABLES, ids=lambda t: t.name)
def test_every_table_records_creation_time(table: Table) -> None:
    time_columns = {"created_at", "occurred_at"}
    assert time_columns & set(table.columns.keys()), f"{table.name} has no creation timestamp"


@pytest.mark.parametrize("table", TABLES, ids=lambda t: t.name)
def test_every_foreign_key_is_indexed(table: Table) -> None:
    """Unindexed foreign keys make joins and cascading deletes slow."""
    indexed_prefixes: list[list[str]] = [[c.name for c in table.primary_key.columns]]
    indexed_prefixes += [[c.name for c in index.columns] for index in table.indexes]
    indexed_prefixes += [
        [c.name for c in constraint.columns]
        for constraint in table.constraints
        if hasattr(constraint, "columns") and constraint.__class__.__name__ == "UniqueConstraint"
    ]
    for fk in table.foreign_key_constraints:
        fk_columns = [c.name for c in fk.columns]
        covered = any(cols[: len(fk_columns)] == fk_columns for cols in indexed_prefixes)
        assert covered, f"{table.name}.{fk_columns} has no index"


@pytest.mark.parametrize("table", TABLES, ids=lambda t: t.name)
def test_foreign_keys_declare_delete_behaviour(table: Table) -> None:
    for fk in table.foreign_keys:
        assert fk.ondelete in {"CASCADE", "SET NULL"}, f"{table.name}.{fk.parent.name}"


def test_no_secret_like_columns() -> None:
    """Secrets belong in environment variables, never in the database schema."""
    forbidden = {"password", "secret", "api_key", "apikey", "token", "private_key", "credentials"}
    for table in TABLES:
        for column in table.columns:
            looks_secret = column.name in forbidden or any(
                column.name.endswith(f"_{word}") for word in forbidden
            )
            assert not looks_secret, f"{table.name}.{column.name} looks like a secret"


def test_embedding_dimension() -> None:
    column = Base.metadata.tables[f"{APP_SCHEMA}.embeddings"].columns["embedding"]
    assert column.type.dim == EMBEDDING_DIMENSIONS == 1024  # type: ignore[attr-defined]
