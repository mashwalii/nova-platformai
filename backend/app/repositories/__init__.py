"""Data access layer."""

from app.repositories.base import BaseRepository
from app.repositories.system import SystemRepository

__all__ = ["BaseRepository", "SystemRepository"]
