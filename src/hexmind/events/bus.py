"""EventBus: publish-subscribe event dispatcher."""

from __future__ import annotations

import asyncio
import logging
from collections import defaultdict
from typing import Protocol, runtime_checkable

from hexmind.events.types import Event, EventType

logger = logging.getLogger(__name__)


@runtime_checkable
class EventListener(Protocol):
    """Any object that can receive events."""

    async def on_event(self, event: Event) -> None: ...


class EventBus:
    """Simple async pub-sub event bus."""

    def __init__(self) -> None:
        self._listeners: list[EventListener] = []
        self._type_listeners: dict[EventType, list[EventListener]] = defaultdict(list)

    def subscribe(
        self,
        listener: EventListener,
        event_types: list[EventType] | None = None,
    ) -> None:
        if event_types:
            for t in event_types:
                self._type_listeners[t].append(listener)
        else:
            self._listeners.append(listener)

    def unsubscribe(self, listener: EventListener) -> None:
        self._listeners = [l for l in self._listeners if l is not listener]
        for t in self._type_listeners:
            self._type_listeners[t] = [
                l for l in self._type_listeners[t] if l is not listener
            ]

    def get_listeners(self) -> list[EventListener]:
        """Return a snapshot of all global listeners."""
        return list(self._listeners)

    async def emit(self, event: Event) -> None:
        targets = self._listeners + self._type_listeners.get(event.type, [])
        results = await asyncio.gather(
            *(l.on_event(event) for l in targets),
            return_exceptions=True,
        )
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                logger.error("EventListener %s raised %s", targets[i], result)
