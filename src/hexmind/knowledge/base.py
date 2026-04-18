"""Knowledge source protocol and shared data models."""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from pydantic import AliasChoices, BaseModel, Field


# ── Data models ────────────────────────────────────────────


class SourceFilters(BaseModel):
    """Filters applied to knowledge source searches."""

    year_min: int | None = None
    year_max: int | None = None
    language: str | None = None
    fields: list[str] = []


class KnowledgeItem(BaseModel):
    """A single knowledge result returned by a source."""

    id: str
    source: str  # "semantic_scholar" | "arxiv" | "local_files" | ...
    title: str
    snippet: str = ""  # abstract / excerpt (≤ 200 chars)
    url: str | None = None
    year: int | None = None
    authors: list[str] = []
    relevance_score: float = Field(default=0.0, ge=0.0, le=1.0)
    citation_count: int | None = None
    provider_metadata: dict = Field(
        default_factory=dict,
        validation_alias=AliasChoices("provider_metadata", "metadata"),
    )

    @property
    def metadata(self) -> dict:
        return self.provider_metadata


class KnowledgeItemDetail(KnowledgeItem):
    """Extended item with full text (for sources that support it)."""

    abstract: str = ""
    full_text: str | None = None
    references: list[str] = []


class RateLimit(BaseModel):
    """Rate limit specification for a knowledge source."""

    max_per_window: int
    window_seconds: int


class PlannedQuery(BaseModel):
    """A search query planned by the QueryPlanner."""

    query: str
    target_sources: list[str] = []  # source_ids to search
    rationale: str = ""


# ── Protocol ───────────────────────────────────────────────


@runtime_checkable
class KnowledgeSource(Protocol):
    """All knowledge sources implement this interface."""

    @property
    def source_id(self) -> str: ...

    @property
    def source_name(self) -> str: ...

    @property
    def rate_limit(self) -> RateLimit | None: ...

    async def search(
        self,
        query: str,
        max_results: int = 5,
        filters: SourceFilters | None = None,
    ) -> list[KnowledgeItem]: ...
