"""ArchiveSearch: keyword search across archived discussions."""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from hexmind.archive.reader import ArchiveEntry, ArchiveReader


@dataclass
class SearchHit:
    """A single search match within an archive entry."""

    entry: ArchiveEntry
    field: str  # "question" | "verdict" | "discussion" | "summary"
    snippet: str  # excerpt around match
    score: float = 1.0


@dataclass
class SearchResult:
    """Aggregated search results."""

    query: str
    hits: list[SearchHit] = field(default_factory=list)

    @property
    def count(self) -> int:
        return len(self.hits)


class ArchiveSearch:
    """Simple keyword search across archived discussions."""

    def __init__(self, archive_dir: str = "discussion_archive") -> None:
        self.reader = ArchiveReader(archive_dir)

    def search(self, query: str, max_results: int = 20) -> SearchResult:
        """Search all archives for a keyword/phrase. Case-insensitive."""
        result = SearchResult(query=query)
        pattern = re.compile(re.escape(query), re.IGNORECASE)

        for entry in self.reader.list_entries():
            hits = self._search_entry(entry, pattern)
            result.hits.extend(hits)
            if len(result.hits) >= max_results:
                result.hits = result.hits[:max_results]
                break

        return result

    def _search_entry(
        self, entry: ArchiveEntry, pattern: re.Pattern
    ) -> list[SearchHit]:
        """Search within a single archive entry."""
        hits: list[SearchHit] = []

        # Search question
        if pattern.search(entry.question):
            hits.append(SearchHit(
                entry=entry, field="question",
                snippet=self._extract_snippet(entry.question, pattern),
            ))

        # Search verdict
        if entry.verdict and pattern.search(entry.verdict):
            hits.append(SearchHit(
                entry=entry, field="verdict",
                snippet=self._extract_snippet(entry.verdict, pattern),
            ))

        # Search discussion markdown
        md = entry.discussion_md
        if md and pattern.search(md):
            hits.append(SearchHit(
                entry=entry, field="discussion",
                snippet=self._extract_snippet(md, pattern),
            ))

        # Search decision summary
        summary = entry.summary
        if summary:
            summary_text = summary.decision + " " + summary.reasoning
            if pattern.search(summary_text):
                hits.append(SearchHit(
                    entry=entry, field="summary",
                    snippet=self._extract_snippet(summary_text, pattern),
                ))

        return hits

    @staticmethod
    def _extract_snippet(text: str, pattern: re.Pattern, context: int = 60) -> str:
        """Extract a snippet around the first match."""
        match = pattern.search(text)
        if not match:
            return text[:context]
        start = max(0, match.start() - context)
        end = min(len(text), match.end() + context)
        snippet = text[start:end].strip()
        if start > 0:
            snippet = "..." + snippet
        if end < len(text):
            snippet = snippet + "..."
        return snippet
