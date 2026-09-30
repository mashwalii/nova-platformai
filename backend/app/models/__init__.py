"""Database models.

Every model module is imported here so Alembic's autogenerate sees all tables.
See DATABASE.md for a plain-English description of each table.
"""

from app.models.ai import EMBEDDING_DIMENSIONS, AIClassification, AISummary, Embedding
from app.models.base import APP_SCHEMA, Base, TimestampMixin, UUIDPrimaryKeyMixin
from app.models.briefs import DailyBrief, DailyBriefItem
from app.models.content import (
    AITool,
    Article,
    ContentAuthor,
    ContentItem,
    ContentTag,
    Course,
    LearningPath,
    LearningPathStep,
    Opportunity,
    Paper,
)
from app.models.operations import CollectionJob, ErrorLog, ProcessingLog
from app.models.taxonomy import Author, Category, Source, Tag
from app.models.users import Notification, SavedItem, User, UserInterest, UserPreferences

__all__ = [
    "APP_SCHEMA",
    "EMBEDDING_DIMENSIONS",
    "AIClassification",
    "AISummary",
    "AITool",
    "Article",
    "Author",
    "Base",
    "Category",
    "CollectionJob",
    "ContentAuthor",
    "ContentItem",
    "ContentTag",
    "Course",
    "DailyBrief",
    "DailyBriefItem",
    "Embedding",
    "ErrorLog",
    "LearningPath",
    "LearningPathStep",
    "Notification",
    "Opportunity",
    "Paper",
    "ProcessingLog",
    "SavedItem",
    "Source",
    "Tag",
    "TimestampMixin",
    "UUIDPrimaryKeyMixin",
    "User",
    "UserInterest",
    "UserPreferences",
]
