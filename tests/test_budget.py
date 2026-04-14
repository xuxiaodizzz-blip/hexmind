"""Tests for engine/budget.py - degradation state machine."""

import pytest

from hexmind.engine.budget import BudgetTracker, DegradationLevel
from hexmind.events.bus import EventBus
from hexmind.events.types import Event, EventType
from hexmind.models.config import DiscussionConfig
from hexmind.models.persona import Persona, PersonaTemperature


def _make_persona(pid: str, domain: str = "tech") -> Persona:
    return Persona(
        id=pid,
        name=pid,
        domain=domain,
        description="test",
        temperature=PersonaTemperature(),
    )


def _panelist_event(total_tokens: int) -> Event:
    return Event(
        type=EventType.PANELIST_OUTPUT,
        data={"token_usage": {"total_tokens": total_tokens}, "cost": 0.001},
    )


class TestDegradationLevels:
    @pytest.mark.asyncio
    async def test_starts_normal(self):
        bus = EventBus()
        bt = BudgetTracker(DiscussionConfig(token_budget=10000), bus)
        assert bt.degradation_level == DegradationLevel.NORMAL
        assert not bt.is_exhausted
        assert bt.usage_pct == 0.0

    @pytest.mark.asyncio
    async def test_transitions_to_reduced(self):
        bus = EventBus()
        bt = BudgetTracker(DiscussionConfig(token_budget=10000), bus)
        await bt.on_event(_panelist_event(8100))
        assert bt.degradation_level == DegradationLevel.REDUCED

    @pytest.mark.asyncio
    async def test_transitions_to_minimal(self):
        bus = EventBus()
        bt = BudgetTracker(DiscussionConfig(token_budget=10000), bus)
        await bt.on_event(_panelist_event(9100))
        assert bt.degradation_level == DegradationLevel.MINIMAL

    @pytest.mark.asyncio
    async def test_transitions_to_forced(self):
        bus = EventBus()
        bt = BudgetTracker(DiscussionConfig(token_budget=10000), bus)
        await bt.on_event(_panelist_event(9600))
        assert bt.degradation_level == DegradationLevel.FORCED_CONCLUDE
        assert bt.is_exhausted

    @pytest.mark.asyncio
    async def test_incremental_accumulation(self):
        bus = EventBus()
        bt = BudgetTracker(DiscussionConfig(token_budget=10000), bus)
        await bt.on_event(_panelist_event(4000))
        assert bt.degradation_level == DegradationLevel.NORMAL
        await bt.on_event(_panelist_event(4100))
        assert bt.degradation_level == DegradationLevel.REDUCED
        await bt.on_event(_panelist_event(1000))
        assert bt.degradation_level == DegradationLevel.MINIMAL


class TestEventEmission:
    @pytest.mark.asyncio
    async def test_emits_degradation_changed(self):
        bus = EventBus()
        events_received: list[Event] = []

        class Collector:
            async def on_event(self, event: Event) -> None:
                events_received.append(event)

        bus.subscribe(Collector(), event_types=[EventType.DEGRADATION_CHANGED])
        bt = BudgetTracker(DiscussionConfig(token_budget=10000), bus)
        await bt.on_event(_panelist_event(8100))

        assert len(events_received) == 1
        assert events_received[0].data["new_level"] == "reduced"
        assert events_received[0].data["old_level"] == "normal"

    @pytest.mark.asyncio
    async def test_emits_budget_warning_at_reduced(self):
        bus = EventBus()
        warnings: list[Event] = []

        class Collector:
            async def on_event(self, event: Event) -> None:
                warnings.append(event)

        bus.subscribe(Collector(), event_types=[EventType.BUDGET_WARNING])
        bt = BudgetTracker(DiscussionConfig(token_budget=10000), bus)
        await bt.on_event(_panelist_event(8100))

        assert len(warnings) == 1
        assert warnings[0].data["level"] == "reduced"


class TestPersonaSelection:
    def test_normal_returns_all(self):
        bus = EventBus()
        bt = BudgetTracker(DiscussionConfig(token_budget=10000), bus)
        personas = [_make_persona("a"), _make_persona("b"), _make_persona("c")]
        assert len(bt.get_active_personas(personas)) == 3

    @pytest.mark.asyncio
    async def test_reduced_returns_max_3(self):
        bus = EventBus()
        bt = BudgetTracker(DiscussionConfig(token_budget=10000), bus)
        await bt.on_event(_panelist_event(8100))
        personas = [
            _make_persona("a", "tech"),
            _make_persona("b", "business"),
            _make_persona("c", "medical"),
            _make_persona("d", "tech"),
            _make_persona("e", "business"),
        ]
        active = bt.get_active_personas(personas)
        assert len(active) == 3

    @pytest.mark.asyncio
    async def test_minimal_returns_max_2(self):
        bus = EventBus()
        bt = BudgetTracker(DiscussionConfig(token_budget=10000), bus)
        await bt.on_event(_panelist_event(9100))
        personas = [_make_persona("a"), _make_persona("b"), _make_persona("c")]
        active = bt.get_active_personas(personas)
        assert len(active) == 2

    @pytest.mark.asyncio
    async def test_forced_returns_empty(self):
        bus = EventBus()
        bt = BudgetTracker(DiscussionConfig(token_budget=10000), bus)
        await bt.on_event(_panelist_event(9600))
        personas = [_make_persona("a")]
        assert bt.get_active_personas(personas) == []

    def test_diverse_selection_covers_domains(self):
        personas = [
            _make_persona("tech1", "tech"),
            _make_persona("tech2", "tech"),
            _make_persona("biz1", "business"),
            _make_persona("med1", "medical"),
        ]
        selected = BudgetTracker._select_diverse_personas(personas, max_count=3)
        domains = {p.domain for p in selected}
        assert len(domains) == 3

    def test_diverse_selection_preserves_remaining_order(self):
        personas = [
            _make_persona("tech1", "tech"),
            _make_persona("biz1", "business"),
            _make_persona("tech2", "tech"),
            _make_persona("tech3", "tech"),
        ]
        selected = BudgetTracker._select_diverse_personas(personas, max_count=3)
        assert [p.id for p in selected] == ["biz1", "tech1", "tech2"]

    def test_diverse_selection_respects_max(self):
        personas = [_make_persona(f"p{i}") for i in range(10)]
        selected = BudgetTracker._select_diverse_personas(personas, max_count=2)
        assert len(selected) == 2


class TestRemainingTokens:
    def test_remaining(self):
        bus = EventBus()
        bt = BudgetTracker(DiscussionConfig(token_budget=10000), bus)
        bt.total_tokens = 3000
        assert bt.remaining_tokens == 7000

    def test_remaining_clamped(self):
        bus = EventBus()
        bt = BudgetTracker(DiscussionConfig(token_budget=10000), bus)
        bt.total_tokens = 15000
        assert bt.remaining_tokens == 0


class TestRecordTokens:
    @pytest.mark.asyncio
    async def test_manual_record(self):
        bus = EventBus()
        bt = BudgetTracker(DiscussionConfig(token_budget=10000), bus)
        await bt.record_tokens(1000, cost=0.05)
        assert bt.total_tokens == 1000
        assert bt.total_cost == 0.05
