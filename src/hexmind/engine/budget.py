"""BudgetTracker: 4-level degradation state machine for token budget."""

from __future__ import annotations

from enum import Enum

from hexmind.events.bus import EventBus
from hexmind.events.types import Event, EventType
from hexmind.models.config import DiscussionConfig
from hexmind.models.persona import Persona


class DegradationLevel(str, Enum):
    """4-level token budget degradation."""

    NORMAL = "normal"  # 0–80%: full power
    REDUCED = "reduced"  # 80–90%: fewer personas + force compression
    MINIMAL = "minimal"  # 90–95%: cheapest model + minimal personas
    FORCED_CONCLUDE = "forced"  # 95–100%: stop and conclude


# Thresholds (usage_pct >= threshold → enter that level)
_LEVEL_THRESHOLDS: dict[DegradationLevel, float] = {
    DegradationLevel.REDUCED: 0.80,
    DegradationLevel.MINIMAL: 0.90,
    DegradationLevel.FORCED_CONCLUDE: 0.95,
}


class BudgetTracker:
    """Track token usage and emit degradation events.

    Listens to PANELIST_OUTPUT events to accumulate token counts.
    Automatically transitions between degradation levels.
    """

    def __init__(self, config: DiscussionConfig, event_bus: EventBus) -> None:
        self.config = config
        self.bus = event_bus
        self.total_tokens: int = 0
        self.total_cost: float = 0.0
        self._level = DegradationLevel.NORMAL

    # ── Properties ─────────────────────────────────────────────

    @property
    def degradation_level(self) -> DegradationLevel:
        return self._level

    @property
    def is_exhausted(self) -> bool:
        return self._level == DegradationLevel.FORCED_CONCLUDE

    @property
    def usage_pct(self) -> float:
        if self.config.token_budget <= 0:
            return 1.0
        return self.total_tokens / self.config.token_budget

    @property
    def remaining_tokens(self) -> int:
        return max(0, self.config.token_budget - self.total_tokens)

    # ── Event listener ─────────────────────────────────────────

    async def on_event(self, event: Event) -> None:
        """Process events to track token usage."""
        if event.type == EventType.PANELIST_OUTPUT:
            usage = event.data.get("token_usage", {})
            self.total_tokens += usage.get("total_tokens", 0)
            self.total_cost += event.data.get("cost", 0.0)

        # Also count compression token cost if tracked
        if event.type == EventType.CONTEXT_COMPRESSED:
            self.total_tokens += event.data.get("tokens_used", 0)

        await self._check_degradation()

    async def _check_degradation(self) -> None:
        new_level = self._compute_level()
        if new_level != self._level:
            old_level = self._level
            self._level = new_level
            await self.bus.emit(
                Event(
                    type=EventType.DEGRADATION_CHANGED,
                    data={
                        "old_level": old_level.value,
                        "new_level": new_level.value,
                        "used_pct": self.usage_pct,
                        "total_tokens": self.total_tokens,
                        "total_cost": self.total_cost,
                    },
                )
            )
            # Also emit budget warning at REDUCED threshold
            if new_level == DegradationLevel.REDUCED:
                await self.bus.emit(
                    Event(
                        type=EventType.BUDGET_WARNING,
                        data={
                            "used_pct": self.usage_pct,
                            "level": new_level.value,
                        },
                    )
                )

    def _compute_level(self) -> DegradationLevel:
        pct = self.usage_pct
        if pct >= _LEVEL_THRESHOLDS[DegradationLevel.FORCED_CONCLUDE]:
            return DegradationLevel.FORCED_CONCLUDE
        if pct >= _LEVEL_THRESHOLDS[DegradationLevel.MINIMAL]:
            return DegradationLevel.MINIMAL
        if pct >= _LEVEL_THRESHOLDS[DegradationLevel.REDUCED]:
            return DegradationLevel.REDUCED
        return DegradationLevel.NORMAL

    # ── Persona selection ──────────────────────────────────────

    def get_active_personas(self, all_personas: list[Persona]) -> list[Persona]:
        """Return available personas based on degradation level."""
        if self._level == DegradationLevel.NORMAL:
            return list(all_personas)
        if self._level == DegradationLevel.REDUCED:
            return self._select_diverse_personas(all_personas, max_count=3)
        if self._level == DegradationLevel.MINIMAL:
            return self._select_diverse_personas(all_personas, max_count=2)
        return []  # FORCED_CONCLUDE: no more discussion

    @staticmethod
    def _select_diverse_personas(
        personas: list[Persona], max_count: int
    ) -> list[Persona]:
        """Pick personas ensuring domain diversity, then stable fill order.

        1. Round-robin one persona per domain
        2. Fill remaining slots in original order
        """
        if len(personas) <= max_count:
            return list(personas)

        by_domain: dict[str, list[Persona]] = {}
        for p in personas:
            by_domain.setdefault(p.domain, []).append(p)

        selected: list[Persona] = []
        # Round-robin across domains
        for domain in sorted(by_domain):
            if len(selected) >= max_count:
                break
            selected.append(by_domain[domain][0])

        # Fill remaining in original order
        selected_ids = {p.id for p in selected}
        remaining = [p for p in personas if p.id not in selected_ids]
        for p in remaining:
            if len(selected) >= max_count:
                break
            selected.append(p)

        return selected

    # ── Manual token recording ─────────────────────────────────

    async def record_tokens(self, tokens: int, cost: float = 0.0) -> None:
        """Manually record token usage (e.g. for blue hat calls)."""
        self.total_tokens += tokens
        self.total_cost += cost
        await self._check_degradation()
