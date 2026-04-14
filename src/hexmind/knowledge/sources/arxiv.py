"""arXiv knowledge source — free preprint search via Atom API."""

from __future__ import annotations

import logging
import xml.etree.ElementTree as ET

import httpx

from hexmind.knowledge.base import (
    KnowledgeItem,
    RateLimit,
    SourceFilters,
)

logger = logging.getLogger(__name__)

_ATOM_NS = "{http://www.w3.org/2005/Atom}"


class ArxivSource:
    """Search arXiv preprints via the public query API (no key required)."""

    BASE_URL = "http://export.arxiv.org/api/query"

    def __init__(self) -> None:
        self._client = httpx.AsyncClient(timeout=15.0)

    # ── KnowledgeSource protocol ───────────────────────────

    @property
    def source_id(self) -> str:
        return "arxiv"

    @property
    def source_name(self) -> str:
        return "arXiv"

    @property
    def rate_limit(self) -> RateLimit:
        return RateLimit(max_per_window=100, window_seconds=60)

    async def search(
        self,
        query: str,
        max_results: int = 5,
        filters: SourceFilters | None = None,
    ) -> list[KnowledgeItem]:
        params = {
            "search_query": f"all:{query}",
            "start": 0,
            "max_results": min(max_results, 20),
            "sortBy": "relevance",
        }

        try:
            resp = await self._client.get(self.BASE_URL, params=params)
            resp.raise_for_status()
        except httpx.HTTPStatusError as e:
            logger.error("arXiv API error: %s", e.response.status_code)
            return []

        return self._parse_atom(resp.text)

    # ── Atom XML parsing ───────────────────────────────────

    def _parse_atom(self, xml_text: str) -> list[KnowledgeItem]:
        try:
            root = ET.fromstring(xml_text)
        except ET.ParseError:
            logger.error("arXiv XML parse error")
            return []
        items: list[KnowledgeItem] = []

        for entry in root.findall(f"{_ATOM_NS}entry"):
            arxiv_id = (entry.findtext(f"{_ATOM_NS}id") or "").rsplit("/", 1)[-1]
            title = (entry.findtext(f"{_ATOM_NS}title") or "").strip()
            abstract = (entry.findtext(f"{_ATOM_NS}summary") or "").strip()
            published = entry.findtext(f"{_ATOM_NS}published") or ""
            year = int(published[:4]) if len(published) >= 4 else None

            authors = [
                (a.findtext(f"{_ATOM_NS}name") or "").strip()
                for a in entry.findall(f"{_ATOM_NS}author")
            ]

            # Prefer PDF link
            url = None
            for link in entry.findall(f"{_ATOM_NS}link"):
                if link.get("title") == "pdf":
                    url = link.get("href")
                    break
                if link.get("type") == "text/html":
                    url = link.get("href")

            items.append(
                KnowledgeItem(
                    id=f"arxiv:{arxiv_id}",
                    source=self.source_id,
                    title=title,
                    snippet=abstract[:200],
                    url=url,
                    year=year,
                    authors=authors,
                    relevance_score=0.0,
                )
            )
        return items

    async def close(self) -> None:
        await self._client.aclose()
