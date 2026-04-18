"""Archive backend abstraction: pluggable JSON or DB storage."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Protocol, runtime_checkable


@dataclass
class DiscussionRecord:
    """Portable representation of a discussion for archive backends."""

    id: str
    question: str
    status: str
    config: dict[str, Any]
    verdict: dict[str, Any] | None = None
    confidence: str | None = None
    total_tokens: int = 0
    total_cost_usd: float = 0.0
    model_used: str | None = None
    discussion_locale: str = "zh"
    created_at: str = ""
    completed_at: str | None = None
    duration_seconds: float | None = None
    tags: list[str] = field(default_factory=list)
    tree: dict[str, Any] = field(default_factory=dict)
    personas: list[str] = field(default_factory=list)


@dataclass
class SearchFilters:
    """Filters for archive search."""

    persona: str | None = None
    hat: str | None = None
    tag: str | None = None
    query: str = ""
    limit: int = 20


@dataclass
class DiscussionSummary:
    """Lightweight discussion summary for list views."""

    id: str
    question: str
    status: str
    confidence: str | None
    created_at: str
    tags: list[str] = field(default_factory=list)
    personas: list[str] = field(default_factory=list)


@runtime_checkable
class ArchiveBackend(Protocol):
    """Protocol for archive storage backends."""

    async def save_discussion(self, record: DiscussionRecord) -> str: ...

    async def get_discussion(self, discussion_id: str) -> DiscussionRecord | None: ...

    async def search(self, filters: SearchFilters) -> list[DiscussionSummary]: ...

    async def list_recent(
        self, limit: int = 50, offset: int = 0
    ) -> list[DiscussionSummary]: ...

    async def delete(self, discussion_id: str) -> bool: ...
