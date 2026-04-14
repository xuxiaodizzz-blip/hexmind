"""Semantic Scholar knowledge source — free academic paper search."""

from __future__ import annotations

import logging

import httpx

from hexmind.knowledge.base import (
    KnowledgeItem,
    RateLimit,
    SourceFilters,
)

logger = logging.getLogger(__name__)


class SemanticScholarSource:
    """Search papers via the Semantic Scholar Graph API (free tier)."""

    BASE_URL = "https://api.semanticscholar.org/graph/v1"

    def __init__(self, api_key: str | None = None) -> None:
        headers: dict[str, str] = {}
        if api_key:
            headers["x-api-key"] = api_key
        self._client = httpx.AsyncClient(timeout=15.0, headers=headers)

    # ── KnowledgeSource protocol ───────────────────────────

    @property
    def source_id(self) -> str:
        return "semantic_scholar"

    @property
    def source_name(self) -> str:
        return "Semantic Scholar"

    @property
    def rate_limit(self) -> RateLimit:
        return RateLimit(max_per_window=100, window_seconds=300)

    async def search(
        self,
        query: str,
        max_results: int = 5,
        filters: SourceFilters | None = None,
    ) -> list[KnowledgeItem]:
        params: dict[str, str | int] = {
            "query": query,
            "limit": min(max_results, 20),
            "fields": "title,abstract,url,year,authors,citationCount",
        }
        if filters and filters.year_min:
            params["year"] = f"{filters.year_min}-"
        if filters and filters.fields:
            params["fieldsOfStudy"] = ",".join(filters.fields)

        try:
            resp = await self._client.get(
                f"{self.BASE_URL}/paper/search", params=params
            )
            resp.raise_for_status()
        except httpx.HTTPStatusError as e:
            logger.error("Semantic Scholar API error: %s", e.response.status_code)
            return []

        items: list[KnowledgeItem] = []
        for paper in resp.json().get("data", []):
            items.append(
                KnowledgeItem(
                    id=f"s2:{paper['paperId']}",
                    source=self.source_id,
                    title=paper.get("title", ""),
                    snippet=(paper.get("abstract") or "")[:200],
                    url=paper.get("url"),
                    year=paper.get("year"),
                    authors=[a["name"] for a in paper.get("authors", [])],
                    citation_count=paper.get("citationCount"),
                    relevance_score=0.0,  # ranked by Ranker later
                )
            )
        return items

    async def close(self) -> None:
        await self._client.aclose()
