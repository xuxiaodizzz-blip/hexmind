"""JSON-file archive backend adapter (Phase 2 compatible)."""

from __future__ import annotations

import json
from pathlib import Path

from hexmind.archive.backend import (
    ArchiveBackend,
    DiscussionRecord,
    DiscussionSummary,
    SearchFilters,
)
from hexmind.archive.reader import ArchiveReader
from hexmind.archive.search import ArchiveSearch


class JSONArchive:
    """Wraps the existing file-based archive as an ArchiveBackend."""

    def __init__(self, archive_dir: str = "discussion_archive") -> None:
        self._dir = archive_dir
        self._reader = ArchiveReader(archive_dir)
        self._search = ArchiveSearch(archive_dir)

    async def save_discussion(self, record: DiscussionRecord) -> str:
        # JSON archive writes are handled by the archive_writer consumer.
        # This is a no-op adapter; the existing EventBus consumer writes files.
        return record.id

    async def get_discussion(self, discussion_id: str) -> DiscussionRecord | None:
        entry = self._reader.get_entry(discussion_id)
        if entry is None:
            return None
        tree: dict = {}
        summary = entry.summary
        if summary:
            tree = summary.model_dump()
        return DiscussionRecord(
            id=entry.dir_name,
            question=entry.question,
            status=entry.status,
            config={},
            verdict={"summary": entry.verdict} if entry.verdict else None,
            confidence=entry.confidence or None,
            created_at=entry.created_at,
            tags=[],
            tree=tree,
            personas=entry.personas,
        )

    async def search(self, filters: SearchFilters) -> list[DiscussionSummary]:
        if not filters.query:
            return await self.list_recent(limit=filters.limit)
        sr = self._search.search(filters.query, max_results=filters.limit)
        seen: set[str] = set()
        summaries: list[DiscussionSummary] = []
        for hit in sr.hits:
            key = hit.entry.dir_name
            if key in seen:
                continue
            seen.add(key)
            summaries.append(
                DiscussionSummary(
                    id=key,
                    question=hit.entry.question,
                    status=hit.entry.status,
                    confidence=hit.entry.confidence or None,
                    created_at=hit.entry.created_at,
                    personas=hit.entry.personas,
                )
            )
        return summaries

    async def list_recent(
        self, limit: int = 50, offset: int = 0
    ) -> list[DiscussionSummary]:
        entries = self._reader.list_entries()
        sliced = entries[offset : offset + limit]
        return [
            DiscussionSummary(
                id=e.dir_name,
                question=e.question,
                status=e.status,
                confidence=e.confidence or None,
                created_at=e.created_at,
                personas=e.personas,
            )
            for e in sliced
        ]

    async def delete(self, discussion_id: str) -> bool:
        entry = self._reader.get_entry(discussion_id)
        if entry is None:
            return False
        import asyncio
        import shutil

        await asyncio.to_thread(shutil.rmtree, entry.path)
        return True
