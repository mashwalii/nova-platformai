"""Database models.

Import every model module here so Alembic's autogenerate can see all tables.
There are no application tables yet — they arrive in Phase 3.
"""

from app.models.base import APP_SCHEMA, Base, TimestampMixin, UUIDPrimaryKeyMixin

__all__ = ["APP_SCHEMA", "Base", "TimestampMixin", "UUIDPrimaryKeyMixin"]
