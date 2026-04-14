"""Citation manager — tracks references and generates bibliography."""

from __future__ import annotations

from hexmind.knowledge.base import KnowledgeItem


class CitationManager:
    """Assigns [N] citation numbers and renders a bibliography.

    Same KnowledgeItem is never double-numbered; subsequent cite() calls
    return the existing number.
    """

    def __init__(self) -> None:
        self._id_to_number: dict[str, int] = {}
        self._items: dict[int, KnowledgeItem] = {}
        self._counter: int = 0

    # ── Public API ─────────────────────────────────────────

    def cite(self, item: KnowledgeItem) -> str:
        """Return a citation marker ``[N]``, assigning a new number if needed."""
        if item.id in self._id_to_number:
            return f"[{self._id_to_number[item.id]}]"
        self._counter += 1
        self._id_to_number[item.id] = self._counter
        self._items[self._counter] = item
        return f"[{self._counter}]"

    def get_item(self, number: int) -> KnowledgeItem | None:
        return self._items.get(number)

    @property
    def count(self) -> int:
        return self._counter

    @property
    def all_items(self) -> list[KnowledgeItem]:
        return [self._items[n] for n in sorted(self._items)]

    def render_bibliography(self) -> str:
        """Render an ordered reference list (APA-ish style)."""
        if not self._items:
            return ""
        lines = ["## 参考文献\n"]
        for num in sorted(self._items):
            item = self._items[num]
            authors = ", ".join(item.authors[:3])
            if len(item.authors) > 3:
                authors += " et al."
            year = f" ({item.year})" if item.year else ""
            url = f" {item.url}" if item.url else ""
            lines.append(f"[{num}] {authors}{year}. {item.title}.{url}")
        return "\n".join(lines)
