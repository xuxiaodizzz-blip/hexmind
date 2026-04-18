"""Tests for engine/budget.py - degradation state machine."""

import pytest

from hexmind.engine.budget import BudgetTracker, DegradationLevel
from hexmind.events.bus import EventBus
from hexmind.events.types import (
    BudgetWarningPayload,
    DegradationChangedPayload,
    Event,
    EventType,
    PanelistOutputPayload,
)
from hexmind.models.config import DiscussionConfig
from hexmind.models.llm import TokenUsage
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
        payload=PanelistOutputPayload(
            token_usage=TokenUsage(total_tokens=total_tokens),
        ),
    )


def _exploration_config(
    exploration_token_cap: int = 10_000,
    finalization_reserve_token_cap: int = 2_500,
) -> DiscussionConfig:
    return DiscussionConfig(
        execution_token_cap=exploration_token_cap + finalization_reserve_token_cap,
        exploration_token_cap=exploration_token_cap,
        finalization_reserve_token_cap=finalization_reserve_token_cap,
    )


class TestDegradationLevels:
    @pytest.mark.asyncio
    async def test_starts_normal(self):
        bus = EventBus()
        bt = BudgetTracker(_exploration_config(), bus)
        assert bt.degradation_level == DegradationLevel.NORMAL
        assert not bt.is_exhausted
        assert bt.usage_pct == 0.0

    @pytest.mark.asyncio
    async def test_transitions_to_reduced(self):
        bus = EventBus()
        bt = BudgetTracker(_exploration_config(), bus)
        await bt.on_event(_panelist_event(8100))
        assert bt.degradation_level == DegradationLevel.REDUCED

    @pytest.mark.asyncio
    async def test_transitions_to_minimal(self):
        bus = EventBus()
        bt = BudgetTracker(_exploration_config(), bus)
        await bt.on_event(_panelist_event(9100))
        assert bt.degradation_level == DegradationLevel.MINIMAL

    @pytest.mark.asyncio
    async def test_transitions_to_forced(self):
        bus = EventBus()
        bt = BudgetTracker(_exploration_config(), bus)
        await bt.on_event(_panelist_event(9600))
        assert bt.degradation_level == DegradationLevel.FORCED_CONCLUDE
        assert bt.is_exhausted

    @pytest.mark.asyncio
    async def test_incremental_accumulation(self):
        bus = EventBus()
        bt = BudgetTracker(_exploration_config(), bus)
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
        bt = BudgetTracker(_exploration_config(), bus)
        await bt.on_event(_panelist_event(8100))

        assert len(events_received) == 1
        payload = events_received[0].payload_as(DegradationChangedPayload)
        assert payload is not None
        assert payload.new_level == "reduced"
        assert payload.old_level == "normal"

    @pytest.mark.asyncio
    async def test_emits_budget_warning_at_reduced(self):
        bus = EventBus()
        warnings: list[Event] = []

        class Collector:
            async def on_event(self, event: Event) -> None:
                warnings.append(event)

        bus.subscribe(Collector(), event_types=[EventType.BUDGET_WARNING])
        bt = BudgetTracker(_exploration_config(), bus)
        await bt.on_event(_panelist_event(8100))

        assert len(warnings) == 1
        payload = warnings[0].payload_as(BudgetWarningPayload)
        assert payload is not None
        assert payload.level == "reduced"


class TestPersonaSelection:
    def test_normal_returns_all(self):
        bus = EventBus()
        bt = BudgetTracker(_exploration_config(), bus)
        personas = [_make_persona("a"), _make_persona("b"), _make_persona("c")]
        assert len(bt.get_active_personas(personas)) == 3

    @pytest.mark.asyncio
    async def test_reduced_returns_max_3(self):
        bus = EventBus()
        bt = BudgetTracker(_exploration_config(), bus)
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
        bt = BudgetTracker(_exploration_config(), bus)
        await bt.on_event(_panelist_event(9100))
        personas = [_make_persona("a"), _make_persona("b"), _make_persona("c")]
        active = bt.get_active_personas(personas)
        assert len(active) == 2

    @pytest.mark.asyncio
    async def test_forced_returns_empty(self):
        bus = EventBus()
        bt = BudgetTracker(_exploration_config(), bus)
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
