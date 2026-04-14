"""KnowledgeHub — aggregate multiple knowledge sources with rate limiting."""

from __future__ import annotations

import asyncio
import logging
import time

from hexmind.knowledge.base import (
    KnowledgeItem,
    KnowledgeSource,
    PlannedQuery,
    SourceFilters,
)

logger = logging.getLogger(__name__)


class _RateLimitTracker:
    """Simple sliding-window request counter per source."""

    def __init__(self) -> None:
        self._windows: dict[str, list[float]] = {}

    def allow(self, source_id: str, max_per_window: int, window_seconds: int) -> bool:
        now = time.monotonic()
        timestamps = self._windows.setdefault(source_id, [])
        cutoff = now - window_seconds
        timestamps[:] = [t for t in timestamps if t > cutoff]
        if len(timestamps) >= max_per_window:
            return False
        timestamps.append(now)
        return True


class KnowledgeHub:
    """Registry + aggregator for all knowledge sources.

    Searches sources in parallel, respects rate limits, and gracefully
    degrades when individual sources fail.
    """

    def __init__(self) -> None:
        self._sources: dict[str, KnowledgeSource] = {}
        self._rate_tracker = _RateLimitTracker()

    # ── Source management ──────────────────────────────────

    def register_source(self, source: KnowledgeSource) -> None:
        self._sources[source.source_id] = source

    def get_available_sources(self) -> list[str]:
        return list(self._sources.keys())

    # ── Search ─────────────────────────────────────────────

    async def search(
        self,
        query: str,
        sources: list[str] | None = None,
        max_results_per_source: int = 3,
        filters: SourceFilters | None = None,
    ) -> list[KnowledgeItem]:
        """Search across registered sources in parallel.

        Returns combined results sorted by relevance_score descending.
        Sources that fail or are rate-limited are silently skipped.
        """
        target_ids = sources or list(self._sources.keys())
        targets = [
            self._sources[sid] for sid in target_ids if sid in self._sources
        ]
        if not targets:
            return []

        tasks = [
            self._safe_search(src, query, max_results_per_source, filters)
            for src in targets
        ]
        results = await asyncio.gather(*tasks)

        combined: list[KnowledgeItem] = []
        for items in results:
            combined.extend(items)

        combined.sort(key=lambda x: x.relevance_score, reverse=True)
        return combined

    async def search_multi(
        self,
        queries: list[PlannedQuery],
        max_results_per_source: int = 3,
        filters: SourceFilters | None = None,
    ) -> list[KnowledgeItem]:
        """Execute multiple planned queries and deduplicate results."""
        seen_ids: set[str] = set()
        all_items: list[KnowledgeItem] = []

        for pq in queries:
            items = await self.search(
                query=pq.query,
                sources=pq.target_sources or None,
                max_results_per_source=max_results_per_source,
                filters=filters,
            )
            for item in items:
                if item.id not in seen_ids:
                    seen_ids.add(item.id)
                    all_items.append(item)

        all_items.sort(key=lambda x: x.relevance_score, reverse=True)
        return all_items

    # ── Internal ───────────────────────────────────────────

    async def _safe_search(
        self,
        source: KnowledgeSource,
        query: str,
        max_results: int,
        filters: SourceFilters | None,
    ) -> list[KnowledgeItem]:
        """Search a single source with rate-limit check and error handling."""
        rl = source.rate_limit
        if rl and not self._rate_tracker.allow(
            source.source_id, rl.max_per_window, rl.window_seconds
        ):
            logger.warning("Rate limit hit for %s, skipping", source.source_id)
            return []

        try:
            return await asyncio.wait_for(
                source.search(query, max_results, filters),
                timeout=15.0,
            )
        except asyncio.TimeoutError:
            logger.warning("Timeout searching %s", source.source_id)
            return []
        except Exception:
            logger.exception("Error searching %s", source.source_id)
            return []
