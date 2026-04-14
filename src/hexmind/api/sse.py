"""SSE streamer: EventBus consumer that bridges events to an async queue."""

from __future__ import annotations

import asyncio
import json
import logging
from collections import deque

from hexmind.events.types import Event, EventType

logger = logging.getLogger(__name__)

# Terminal events — after these the SSE stream should close.
_TERMINAL_EVENTS = frozenset(
    {EventType.CONCLUSION, EventType.DISCUSSION_CANCELLED, EventType.ERROR}
)


class SSEStreamer:
    """Subscribes to EventBus; each connected SSE client gets a QueueListener.

    Also maintains a replay buffer so reconnecting clients can catch up.
    """

    def __init__(self, replay_limit: int = 100) -> None:
        self._replay: deque[dict] = deque(maxlen=replay_limit)
        self._listeners: list[asyncio.Queue[dict | None]] = []
        self._event_index: int = 0
        self._finished = False

    # ── EventBus interface ──────────────────────────────────

    async def on_event(self, event: Event) -> None:
        """Called by EventBus.emit() — fan out to all connected queues."""
        payload = self._serialize(event)
        self._replay.append(payload)

        dead: list[asyncio.Queue] = []
        for q in self._listeners:
            try:
                q.put_nowait(payload)
            except asyncio.QueueFull:
                dead.append(q)
        for q in dead:
            self._listeners.remove(q)

        if event.type in _TERMINAL_EVENTS:
            self._finished = True
            # Signal all listeners that stream is done
            for q in self._listeners:
                try:
                    q.put_nowait(None)
                except asyncio.QueueFull:
                    pass

    # ── SSE client interface ────────────────────────────────

    def create_listener(
        self, last_event_id: int | None = None
    ) -> asyncio.Queue[dict | None]:
        """Create a new listener queue, optionally replaying missed events."""
        q: asyncio.Queue[dict | None] = asyncio.Queue(maxsize=500)

        # Replay buffered events after last_event_id
        if last_event_id is not None:
            for item in self._replay:
                if item["id"] > last_event_id:
                    q.put_nowait(item)
        else:
            # New connection: replay everything
            for item in self._replay:
                q.put_nowait(item)

        if self._finished:
            q.put_nowait(None)
        else:
            self._listeners.append(q)

        return q

    def remove_listener(self, q: asyncio.Queue) -> None:
        try:
            self._listeners.remove(q)
        except ValueError:
            pass

    @property
    def finished(self) -> bool:
        return self._finished

    # ── Serialization ───────────────────────────────────────

    def _serialize(self, event: Event) -> dict:
        self._event_index += 1
        return {
            "id": self._event_index,
            "event": event.type.value,
            "data": json.dumps(event.data, ensure_ascii=False),
        }
