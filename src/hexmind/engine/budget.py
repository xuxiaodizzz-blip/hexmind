"""BudgetTracker: degradation state machine for exploration budget."""

from __future__ import annotations

from enum import Enum

from hexmind.events.bus import EventBus
from hexmind.events.types import (
    BudgetWarningPayload,
    ContextCompressedPayload,
    DegradationChangedPayload,
    Event,
    EventType,
    PanelistOutputPayload,
)
from hexmind.models.config import DiscussionConfig
from hexmind.models.persona import Persona


class DegradationLevel(str, Enum):
    """Exploration degradation levels before forced convergence."""

    NORMAL = "normal"
    REDUCED = "reduced"
    MINIMAL = "minimal"
    FORCED_CONCLUDE = "forced_conclude"


class BudgetTracker:
    """Track token usage and emit degradation events.

    The tracker now treats ``exploration_token_cap`` as the active budget for
    multi-round discussion. ``finalization_reserve_token_cap`` is intentionally
    excluded from degradation math so the engine can still synthesize an answer
    after exploration is cut short.
    """

    def __init__(self, config: DiscussionConfig, event_bus: EventBus) -> None:
        self.config = config
        self.bus = event_bus
        self.total_tokens: int = 0
        self.total_cost: float = 0.0
        self._level = DegradationLevel.NORMAL

    @property
    def degradation_level(self) -> DegradationLevel:
        return self._level

    @property
    def is_exhausted(self) -> bool:
        return self.should_force_conclude

    @property
    def should_force_conclude(self) -> bool:
        return self._level == DegradationLevel.FORCED_CONCLUDE

    @property
    def is_execution_exhausted(self) -> bool:
        return self.total_tokens >= self.config.execution_token_cap

    @property
    def usage_pct(self) -> float:
        """Exploration usage percentage used for degradation thresholds."""

        if not self.config.exploration_token_cap or self.config.exploration_token_cap <= 0:
            return 1.0
        return self.total_tokens / self.config.exploration_token_cap

    @property
    def execution_usage_pct(self) -> float:
        if self.config.execution_token_cap <= 0:
            return 1.0
        return self.total_tokens / self.config.execution_token_cap

    @property
    def remaining_tokens(self) -> int:
        return self.remaining_execution_tokens

    @property
    def remaining_exploration_tokens(self) -> int:
        if not self.config.exploration_token_cap:
            return 0
        return max(0, self.config.exploration_token_cap - self.total_tokens)

    @property
    def remaining_execution_tokens(self) -> int:
        return max(0, self.config.execution_token_cap - self.total_tokens)

    async def on_event(self, event: Event) -> None:
        """Process events to track token usage."""

        if event.type == EventType.PANELIST_OUTPUT:
            payload = event.payload_as(PanelistOutputPayload)
            if payload:
                self.total_tokens += payload.token_usage.total_tokens
                self.total_cost += event.data.get("cost", 0.0)

        if event.type == EventType.CONTEXT_COMPRESSED:
            payload = event.payload_as(ContextCompressedPayload)
            if payload:
                self.total_tokens += payload.tokens_used

        await self._check_degradation()

    async def _check_degradation(self) -> None:
        new_level = self._compute_level()
        if new_level != self._level:
            old_level = self._level
            self._level = new_level
            await self.bus.emit(
                Event(
                    type=EventType.DEGRADATION_CHANGED,
                    payload=DegradationChangedPayload(
                        old_level=old_level.value,
                        new_level=new_level.value,
                        used_pct=self.usage_pct,
                        total_tokens=self.total_tokens,
                        total_cost=self.total_cost,
                    ),
                )
            )
            if new_level == DegradationLevel.REDUCED:
                await self.bus.emit(
                    Event(
                        type=EventType.BUDGET_WARNING,
                        payload=BudgetWarningPayload(
                            used_pct=self.usage_pct,
                            level=new_level.value,
                        ),
                    )
                )

    def _compute_level(self) -> DegradationLevel:
        pct = self.usage_pct
        if pct >= self.config.degradation_forced_pct:
            return DegradationLevel.FORCED_CONCLUDE
        if pct >= self.config.degradation_minimal_pct:
            return DegradationLevel.MINIMAL
        if pct >= self.config.degradation_reduced_pct:
            return DegradationLevel.REDUCED
        return DegradationLevel.NORMAL

    def get_active_personas(self, all_personas: list[Persona]) -> list[Persona]:
        """Return available personas based on degradation level."""

        if self._level == DegradationLevel.NORMAL:
            return list(all_personas)
        if self._level == DegradationLevel.REDUCED:
            return self._select_diverse_personas(all_personas, max_count=3)
        if self._level == DegradationLevel.MINIMAL:
            return self._select_diverse_personas(all_personas, max_count=2)
        return []

    @staticmethod
    def _select_diverse_personas(
        personas: list[Persona], max_count: int
    ) -> list[Persona]:
        """Pick personas ensuring domain diversity, then stable fill order."""

        if len(personas) <= max_count:
            return list(personas)

        by_domain: dict[str, list[Persona]] = {}
        for persona in personas:
            by_domain.setdefault(persona.domain, []).append(persona)

        selected: list[Persona] = []
        for domain in sorted(by_domain):
            if len(selected) >= max_count:
                break
            selected.append(by_domain[domain][0])

        selected_ids = {persona.id for persona in selected}
        remaining = [persona for persona in personas if persona.id not in selected_ids]
        for persona in remaining:
            if len(selected) >= max_count:
                break
            selected.append(persona)

        return selected

    async def record_tokens(self, tokens: int, cost: float = 0.0) -> None:
        """Manually record token usage such as coordinator or verdict calls."""

        self.total_tokens += tokens
        self.total_cost += cost
        await self._check_degradation()
