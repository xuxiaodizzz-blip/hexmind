"""Discussion archive knowledge source — reuse historical verdicts."""

from __future__ import annotations

import re

from hexmind.archive.reader import ArchiveReader
from hexmind.knowledge.base import (
    KnowledgeItem,
    RateLimit,
    SourceFilters,
)


class ArchiveKnowledgeSource:
    """Search past discussion archives for reusable conclusions."""

    def __init__(self, archive_dir: str = "discussion_archive") -> None:
        self._reader = ArchiveReader(archive_dir)

    # ── KnowledgeSource protocol ───────────────────────────

    @property
    def source_id(self) -> str:
        return "archive"

    @property
    def source_name(self) -> str:
        return "Discussion Archive"

    @property
    def rate_limit(self) -> RateLimit | None:
        return None

    async def search(
        self,
        query: str,
        max_results: int = 5,
        filters: SourceFilters | None = None,
    ) -> list[KnowledgeItem]:
        pattern = re.compile(re.escape(query), re.IGNORECASE)
        items: list[KnowledgeItem] = []

        for entry in self._reader.list_entries():
            if len(items) >= max_results:
                break

            # Search question + verdict
            matched = False
            snippet = ""

            if pattern.search(entry.question):
                matched = True
                snippet = entry.question

            if entry.verdict and pattern.search(entry.verdict):
                matched = True
                snippet = entry.verdict[:200]

            if not matched:
                md = entry.discussion_md
                if md and pattern.search(md):
                    matched = True
                    m = pattern.search(md)
                    if m:
                        start = max(0, m.start() - 80)
                        end = min(len(md), m.end() + 120)
                        snippet = md[start:end].strip().replace("\n", " ")[:200]

            if matched:
                items.append(
                    KnowledgeItem(
                        id=f"archive:{entry.dir_name}",
                        source=self.source_id,
                        title=entry.question or entry.dir_name,
                        snippet=snippet,
                        url=None,
                        relevance_score=0.6,
                        metadata={
                            "status": entry.status,
                            "confidence": entry.confidence,
                        },
                    )
                )

        return items
