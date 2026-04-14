"""Local file knowledge source — keyword search across project files."""

from __future__ import annotations

import re
from pathlib import Path

from hexmind.knowledge.base import (
    KnowledgeItem,
    RateLimit,
    SourceFilters,
)

_TEXT_EXTENSIONS = {".md", ".txt", ".rst", ".py", ".ts", ".js", ".yaml", ".yml", ".json"}


class LocalFileSource:
    """Search local project files by keyword matching."""

    def __init__(self, root_dir: str | Path) -> None:
        self._root = Path(root_dir)

    # ── KnowledgeSource protocol ───────────────────────────

    @property
    def source_id(self) -> str:
        return "local_files"

    @property
    def source_name(self) -> str:
        return "Local Files"

    @property
    def rate_limit(self) -> RateLimit | None:
        return None  # no external API

    async def search(
        self,
        query: str,
        max_results: int = 5,
        filters: SourceFilters | None = None,
    ) -> list[KnowledgeItem]:
        if not self._root.is_dir():
            return []

        pattern = re.compile(re.escape(query), re.IGNORECASE)
        items: list[KnowledgeItem] = []

        for path in self._root.rglob("*"):
            if len(items) >= max_results:
                break
            if not path.is_file():
                continue
            if path.suffix.lower() not in _TEXT_EXTENSIONS:
                continue
            # Skip hidden dirs and common noise
            rel = path.relative_to(self._root)
            if any(part.startswith(".") or part == "node_modules" for part in rel.parts):
                continue

            try:
                text = path.read_text(encoding="utf-8", errors="ignore")
            except OSError:
                continue

            match = pattern.search(text)
            if not match:
                continue

            # Extract snippet around match
            start = max(0, match.start() - 80)
            end = min(len(text), match.end() + 120)
            snippet = text[start:end].strip().replace("\n", " ")

            items.append(
                KnowledgeItem(
                    id=f"local:{rel.as_posix()}",
                    source=self.source_id,
                    title=rel.as_posix(),
                    snippet=snippet[:200],
                    url=None,
                    relevance_score=0.5,
                    metadata={"path": str(path)},
                )
            )

        return items
