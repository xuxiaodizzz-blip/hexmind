"""Discussion registry: manage running discussion instances."""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass, field
from typing import Literal

from hexmind.engine.orchestrator import Orchestrator
from hexmind.events.bus import EventBus

logger = logging.getLogger(__name__)


DiscussionStatus = Literal["running", "converged", "partial", "cancelled", "error"]


@dataclass
class DiscussionEntry:
    """A registered discussion instance."""

    discussion_id: str
    question: str
    persona_ids: list[str]
    orchestrator: Orchestrator
    event_bus: EventBus
    user_id: str | None = None
    team_id: str | None = None
    task: asyncio.Task | None = None
    status: DiscussionStatus = "running"


class DiscussionRegistry:
    """In-memory registry of active and recent discussions.

    Thread-safe via asyncio single-threaded event loop.
    Phase 5 replaces this with database-backed persistence.
    """

    def __init__(self, max_recent: int = 100) -> None:
        self._entries: dict[str, DiscussionEntry] = {}
        self._max_recent = max_recent

    def register(
        self,
        discussion_id: str,
        question: str,
        persona_ids: list[str],
        orchestrator: Orchestrator,
        event_bus: EventBus,
        user_id: str | None = None,
        team_id: str | None = None,
    ) -> DiscussionEntry:
        entry = DiscussionEntry(
            discussion_id=discussion_id,
            question=question,
            persona_ids=persona_ids,
            orchestrator=orchestrator,
            event_bus=event_bus,
            user_id=user_id,
            team_id=team_id,
        )
        self._entries[discussion_id] = entry
        self._evict_old()
        return entry

    def get(self, discussion_id: str) -> DiscussionEntry | None:
        return self._entries.get(discussion_id)

    def mark_completed(
        self, discussion_id: str, status: DiscussionStatus = "converged"
    ) -> None:
        entry = self._entries.get(discussion_id)
        if entry:
            entry.status = status

    def list_all(self) -> list[DiscussionEntry]:
        return list(self._entries.values())

    def remove(self, discussion_id: str) -> None:
        self._entries.pop(discussion_id, None)

    def _evict_old(self) -> None:
        """Remove oldest completed entries if over limit."""
        if len(self._entries) <= self._max_recent:
            return
        completed = [
            e
            for e in self._entries.values()
            if e.status != "running"
        ]
        completed.sort(key=lambda e: e.discussion_id)
        for entry in completed[: len(completed) - self._max_recent // 2]:
            self._entries.pop(entry.discussion_id, None)
