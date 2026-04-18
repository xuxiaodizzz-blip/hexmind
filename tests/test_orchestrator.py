"""Tests for engine/orchestrator.py — all LLM calls mocked."""

from __future__ import annotations

import asyncio
import json

import pytest

from hexmind.engine.orchestrator import (
    BlueHatDecision,
    Orchestrator,
    _HAT_RULES,
)
from hexmind.events.bus import EventBus
from hexmind.events.types import (
    BlueHatDecisionPayload,
    ConclusionPayload,
    DiscussionCancelledPayload,
    Event,
    EventType,
    PanelistOutputPayload,
    RoundCompletedPayload,
    RoundStartedPayload,
)
from hexmind.models.config import DiscussionConfig
from hexmind.models.hat import HatColor
from hexmind.models.llm import LLMResponse, TokenPricing, TokenUsage
from hexmind.models.persona import Persona
from hexmind.models.round import OutputItem, PanelistOutput, Round
from hexmind.models.tree import NodeStatus, Verdict


# ── Helpers ────────────────────────────────────────────────


def _usage(total: int = 100) -> TokenUsage:
    return TokenUsage(input_tokens=total // 2, output_tokens=total // 2, total_tokens=total)


def _persona(pid: str = "tester", domain: str = "tech") -> Persona:
    return Persona(
        id=pid,
        name="Test " + pid,
        domain=domain,
        description="Test persona " + pid,
        prompt="Analyze from this role's perspective.",
    )


def _config(**overrides) -> DiscussionConfig:
    defaults = dict(
        max_rounds=4,
        token_budget=100_000,
        max_tree_depth=2,
        max_tree_width=2,
        max_fork_rounds=2,
        max_validation_retries=0,
    )
    defaults.update(overrides)
    return DiscussionConfig(**defaults)


class MockLLM:
    """Mock LLM backend that returns pre-configured responses."""

    def __init__(self, responses: list[str] | None = None) -> None:
        self._responses = list(responses or [])
        self._call_count = 0

    async def complete(
        self,
        system_prompt: str,
        user_prompt: str,
        *,
        temperature: float = 0.7,
        max_tokens: int = 2000,
        response_format: str = "text",
    ) -> LLMResponse:
        self._call_count += 1
        if self._responses:
            content = self._responses.pop(0)
        else:
            content = "default reply"
        return LLMResponse(content=content, usage=_usage(), model="mock")

    def count_tokens(self, text: str) -> int:
        return len(text) // 2

    def count_messages_tokens(self, messages: list[dict[str, str]]) -> int:
        return sum(len(m.get("content", "")) // 2 for m in messages)

    @property
    def context_limit(self) -> int:
        return 128_000

    @property
    def model_name(self) -> str:
        return "mock-model"

    @property
    def pricing(self) -> TokenPricing | None:
        return None


class EventCollector:
    """Collect all emitted events for assertions."""

    def __init__(self) -> None:
        self.events: list[Event] = []

    async def on_event(self, event: Event) -> None:
        self.events.append(event)

    def of_type(self, t: EventType) -> list[Event]:
        return [e for e in self.events if e.type == t]

    def has(self, t: EventType) -> bool:
        return any(e.type == t for e in self.events)


# ── BlueHatDecision model tests ───────────────────────────


def test_blue_hat_decision_discuss():
    d = BlueHatDecision(action="discuss", hat=HatColor.WHITE, reasoning="test")
    assert d.action == "discuss"
    assert d.hat == HatColor.WHITE


def test_blue_hat_decision_converge():
    d = BlueHatDecision(action="converge", reasoning="done")
    assert d.hat is None
    assert d.sub_question is None


def test_blue_hat_decision_fork():
    d = BlueHatDecision(action="fork", sub_question="sub?", reasoning="branch")
    assert d.sub_question == "sub?"


# ── Orchestrator construction ──────────────────────────────


def test_event_payload_as_coerces_legacy_dict_payload():
    event = Event(
        type=EventType.BLUE_HAT_DECISION,
        data={"node_id": "root", "round": 1, "hat": "white", "reasoning": "facts first"},
    )

    payload = event.payload_as(BlueHatDecisionPayload)
    assert payload is not None
    assert payload.hat == HatColor.WHITE
    assert payload.round == 1


def test_orchestrator_init():
    bus = EventBus()
    llm = MockLLM()
    personas = [_persona("a"), _persona("b")]
    config = _config()
    orch = Orchestrator(llm, personas, config, bus)

    assert orch.llm is llm
    assert len(orch.personas) == 2
    assert orch.tree.root is None
    assert not orch._cancel_requested
    assert orch.last_run_status is None


# ── Rule-based fallback ───────────────────────────────────


def test_rule_based_white_first():
    bus = EventBus()
    orch = Orchestrator(MockLLM(), [_persona()], _config(), bus)
    decision = orch._rule_based_decision(
        None, set()  # type: ignore[arg-type]
    )
    assert decision.hat == HatColor.WHITE
    assert decision.action == "discuss"


def test_rule_based_black_after_white():
    orch = Orchestrator(MockLLM(), [_persona()], _config(), EventBus())
    decision = orch._rule_based_decision(None, {"white"})  # type: ignore
    assert decision.hat == HatColor.BLACK


def test_rule_based_converge_all_covered():
    orch = Orchestrator(MockLLM(), [_persona()], _config(), EventBus())
    decision = orch._rule_based_decision(
        None, {"white", "black", "yellow", "green", "red"}  # type: ignore
    )
    assert decision.action == "converge"


# ── Output parsing ─────────────────────────────────────────


def test_parse_white_items():
    content = "W1: fact one\nW2: fact two (ref B1)"
    items = Orchestrator._parse_output_items(content, HatColor.WHITE)
    assert len(items) == 2
    assert items[0].id == "W1"
    assert "fact one" in items[0].content


def test_parse_black_with_refs():
    content = "B1: risk one ref W1 W2\nB2: risk two"
    items = Orchestrator._parse_output_items(content, HatColor.BLACK)
    assert len(items) == 2
    assert "W1" in items[0].references
    assert "W2" in items[0].references


def test_parse_red_hat_returns_empty():
    items = Orchestrator._parse_output_items("intuition: feels good", HatColor.RED)
    assert items == []


def test_parse_green_items():
    content = "G1: plan one for B1\nG2: plan two for B2"
    items = Orchestrator._parse_output_items(content, HatColor.GREEN)
    assert len(items) == 2
    assert "B1" in items[0].references


# ── Panelist prompt building ──────────────────────────────


def test_build_panelist_prompt_includes_hat_rules():
    orch = Orchestrator(MockLLM(), [_persona()], _config(), EventBus())
    persona = _persona("engineer")
    prompt = orch._build_panelist_prompt(persona, HatColor.WHITE)
    assert "White Hat" in prompt
    assert persona.name in prompt


def test_build_panelist_prompt_includes_persona_prompt():
    persona = _persona("engineer")
    orch = Orchestrator(MockLLM(), [persona], _config(), EventBus())
    prompt = orch._build_panelist_prompt(persona, HatColor.WHITE)
    assert persona.prompt in prompt


# ── Context building ──────────────────────────────────────


def test_build_context_includes_question():
    orch = Orchestrator(MockLLM(), [_persona()], _config(), EventBus())
    node = orch.tree.create_root("test question")
    ctx = orch._build_context(node)
    assert "test question" in ctx


def test_build_context_includes_rounds():
    orch = Orchestrator(MockLLM(), [_persona()], _config(), EventBus())
    node = orch.tree.create_root("Q")
    node.rounds.append(
        Round(
            number=1,
            hat=HatColor.WHITE,
            blue_hat_reasoning="",
            outputs=[
                PanelistOutput(
                    persona_id="tester",
                    hat=HatColor.WHITE,
                    content="W1: data point",
                    items=[OutputItem(id="W1", content="data point")],
                    raw_content="W1: data point",
                    token_usage=_usage(),
                    validation_passed=True,
                )
            ],
            timestamp=0.0,
        )
    )
    ctx = orch._build_context(node)
    assert "Round 1" in ctx
    assert "W1: data point" in ctx


# ── Full run (simple converge) ─────────────────────────────


@pytest.mark.asyncio
async def test_run_immediate_converge():
    """Blue Hat immediately converges -> single verdict."""
    converge_json = json.dumps(
        {"action": "converge", "reasoning": "enough"}
    )
    verdict_json = json.dumps(
        {
            "summary": "conclusion",
            "confidence": "high",
            "key_facts": ["F1"],
            "key_risks": [],
            "key_values": [],
            "mitigations": [],
            "intuition_summary": "",
            "blue_hat_ruling": "OK",
            "next_actions": [],
        }
    )
    llm = MockLLM([converge_json, verdict_json])
    bus = EventBus()
    collector = EventCollector()
    bus.subscribe(collector)

    orch = Orchestrator(llm, [_persona()], _config(), bus)
    await orch.run("test question")

    assert collector.has(EventType.DISCUSSION_STARTED)
    assert collector.has(EventType.BLUE_HAT_DECISION)
    assert collector.has(EventType.CONCLUSION)
    assert orch.tree.root.status == NodeStatus.CONVERGED


@pytest.mark.asyncio
async def test_run_one_round_then_converge():
    """Blue Hat requests one White round, then converges."""
    discuss_json = json.dumps(
        {"action": "discuss", "hat": "white", "target_personas": ["tester"], "reasoning": "need data"}
    )
    panelist_response = "W1: test fact one"
    converge_json = json.dumps(
        {"action": "converge", "reasoning": "enough"}
    )
    verdict_json = json.dumps(
        {
            "summary": "conclusion",
            "confidence": "medium",
            "key_facts": [],
            "key_risks": [],
            "key_values": [],
            "mitigations": [],
            "intuition_summary": "",
            "blue_hat_ruling": "OK",
            "next_actions": [],
        }
    )
    llm = MockLLM([discuss_json, panelist_response, converge_json, verdict_json])
    bus = EventBus()
    collector = EventCollector()
    bus.subscribe(collector)

    orch = Orchestrator(llm, [_persona()], _config(), bus)
    await orch.run("question")

    assert len(orch.tree.root.rounds) == 1
    assert orch.tree.root.rounds[0].hat == HatColor.WHITE
    round_started = collector.of_type(EventType.ROUND_STARTED)[0]
    panelist_output = collector.of_type(EventType.PANELIST_OUTPUT)[0]
    round_completed = collector.of_type(EventType.ROUND_COMPLETED)[0]
    blue_hat = collector.of_type(EventType.BLUE_HAT_DECISION)[0]

    assert isinstance(round_started.payload, RoundStartedPayload)
    assert isinstance(panelist_output.payload, PanelistOutputPayload)
    assert isinstance(round_completed.payload, RoundCompletedPayload)
    assert isinstance(blue_hat.payload, BlueHatDecisionPayload)
    assert round_started.data["hat"] == "white"


@pytest.mark.asyncio
async def test_max_rounds_forces_conclude():
    """Hitting max_rounds triggers forced conclusion."""
    discuss_json = json.dumps(
        {"action": "discuss", "hat": "white", "target_personas": ["tester"], "reasoning": "more data"}
    )
    panelist = "W1: data"
    verdict_json = json.dumps(
        {
            "summary": "Max rounds",
            "confidence": "low",
            "key_facts": [],
            "key_risks": [],
            "key_values": [],
            "mitigations": [],
            "intuition_summary": "",
            "blue_hat_ruling": "Forced",
            "next_actions": [],
        }
    )
    responses = [discuss_json, panelist, discuss_json, panelist, verdict_json]
    llm = MockLLM(responses)
    bus = EventBus()
    collector = EventCollector()
    bus.subscribe(collector)

    orch = Orchestrator(llm, [_persona()], _config(max_rounds=2), bus)
    await orch.run("question")

    assert len(orch.tree.root.rounds) == 2
    conclusion_events = collector.of_type(EventType.CONCLUSION)
    assert len(conclusion_events) >= 1


@pytest.mark.asyncio
async def test_cancel_generates_partial_verdict():
    """Requesting cancel produces a partial verdict."""
    verdict_json = json.dumps(
        {
            "summary": "Cancelled",
            "confidence": "low",
            "key_facts": [],
            "key_risks": [],
            "key_values": [],
            "mitigations": [],
            "intuition_summary": "",
            "blue_hat_ruling": "Cancelled",
            "next_actions": [],
        }
    )
    llm = MockLLM([verdict_json])
    bus = EventBus()
    collector = EventCollector()
    bus.subscribe(collector)

    orch = Orchestrator(llm, [_persona()], _config(), bus)
    orch._cancel_requested = True
    await orch.run("question")

    assert orch.tree.root.status == NodeStatus.CANCELLED
    assert orch.last_run_status == NodeStatus.CANCELLED
    cancelled_event = collector.of_type(EventType.DISCUSSION_CANCELLED)[0]
    assert isinstance(cancelled_event.payload, DiscussionCancelledPayload)
    assert cancelled_event.data["partial"] is True


@pytest.mark.asyncio
async def test_run_resets_cancel_flag_after_completion():
    verdict_json = json.dumps(
        {
            "summary": "Cancelled",
            "confidence": "low",
            "key_facts": [],
            "key_risks": [],
            "key_values": [],
            "mitigations": [],
            "intuition_summary": "",
            "blue_hat_ruling": "Cancelled",
            "next_actions": [],
        }
    )
    orch = Orchestrator(MockLLM([verdict_json]), [_persona()], _config(), EventBus())
    await orch.cancel()
    await orch.run("question")
    assert orch.last_run_status == NodeStatus.CANCELLED
    assert orch._cancel_requested is False


def test_get_status_snapshot_exposes_public_metrics():
    orch = Orchestrator(MockLLM(), [_persona()], _config(token_budget=321), EventBus())
    node = orch.tree.create_root("question")
    node.rounds.append(
        Round(
            number=1,
            hat=HatColor.WHITE,
            blue_hat_reasoning="why",
            outputs=[],
            timestamp=0.0,
        )
    )
    orch.budget.total_tokens = 123

    snapshot = orch.get_status_snapshot()
    assert snapshot == {
        "rounds_completed": 1,
        "token_used": 123,
        "execution_token_cap": 321,
        "exploration_token_cap": 257,
        "finalization_reserve_token_cap": 64,
        "billable_tokens": 0,
        "input_tokens": 0,
        "output_tokens": 0,
    }


def test_has_partial_verdict_uses_public_query():
    orch = Orchestrator(MockLLM(), [_persona()], _config(), EventBus())
    node = orch.tree.create_root("question")
    node.verdict = Verdict(
        summary="partial",
        confidence="low",
        key_facts=[],
        key_risks=[],
        key_values=[],
        mitigations=[],
        intuition_summary="",
        blue_hat_ruling="short",
        next_actions=[],
        partial=True,
    )

    assert orch.has_partial_verdict() is True


@pytest.mark.asyncio
async def test_run_tracks_provider_reported_billable_usage():
    discuss_json = json.dumps(
        {"action": "discuss", "hat": "white", "target_personas": ["tester"], "reasoning": "need data"}
    )
    panelist_response = "W1: test fact one"
    converge_json = json.dumps({"action": "converge", "reasoning": "enough"})
    verdict_json = json.dumps(
        {
            "summary": "conclusion",
            "confidence": "medium",
            "key_facts": [],
            "key_risks": [],
            "key_values": [],
            "mitigations": [],
            "intuition_summary": "",
            "blue_hat_ruling": "OK",
            "next_actions": [],
        }
    )
    llm = MockLLM([discuss_json, panelist_response, converge_json, verdict_json])
    bus = EventBus()
    collector = EventCollector()
    bus.subscribe(collector)

    orch = Orchestrator(llm, [_persona()], _config(), bus)
    await orch.run("question")

    usage = orch.get_billable_usage()
    assert usage.input_tokens == 200
    assert usage.output_tokens == 200
    assert usage.total_tokens == 400

    snapshot = orch.get_status_snapshot()
    assert snapshot["billable_tokens"] == 400
    assert snapshot["input_tokens"] == 200
    assert snapshot["output_tokens"] == 200

    conclusion_event = collector.of_type(EventType.CONCLUSION)[0]
    assert isinstance(conclusion_event.payload, ConclusionPayload)
    assert conclusion_event.data["token_usage"]["total_tokens"] == 400


@pytest.mark.asyncio
async def test_budget_exhaustion_forces_conclude():
    """Exhausting token budget triggers forced conclusion."""
    verdict_json = json.dumps(
        {
            "summary": "Budget",
            "confidence": "low",
            "key_facts": [],
            "key_risks": [],
            "key_values": [],
            "mitigations": [],
            "intuition_summary": "",
            "blue_hat_ruling": "Budget exhausted",
            "next_actions": [],
        }
    )
    llm = MockLLM([verdict_json])
    bus = EventBus()
    collector = EventCollector()
    bus.subscribe(collector)

    config = _config(token_budget=100)
    orch = Orchestrator(llm, [_persona()], config, bus)
    orch.budget.total_tokens = 96
    await orch.budget._check_degradation()

    await orch.run("question")

    conclusion_events = collector.of_type(EventType.CONCLUSION)
    assert len(conclusion_events) >= 1


@pytest.mark.asyncio
async def test_time_budget_forces_conclude(monkeypatch):
    verdict_json = json.dumps(
        {
            "summary": "Time budget reached",
            "confidence": "low",
            "key_facts": [],
            "key_risks": [],
            "key_values": [],
            "mitigations": [],
            "intuition_summary": "",
            "blue_hat_ruling": "Stop due to time limit",
            "next_actions": [],
        }
    )
    llm = MockLLM([verdict_json])
    bus = EventBus()
    collector = EventCollector()
    bus.subscribe(collector)

    timestamps = iter([100.0, 101.5, 101.5])
    monkeypatch.setattr(
        "hexmind.engine.orchestrator.time.monotonic",
        lambda: next(timestamps, 101.5),
    )

    orch = Orchestrator(llm, [_persona()], _config(time_budget_seconds=1), bus)
    await orch.run("question")

    conclusion_event = collector.of_type(EventType.CONCLUSION)[0]
    assert conclusion_event.data["force_reason"] == "Time budget exceeded"
    assert conclusion_event.data["duration_seconds"] == pytest.approx(1.5)


# ── Fork tests ─────────────────────────────────────────────


@pytest.mark.asyncio
async def test_fork_creates_child_node():
    """Fork action creates a child discussion node."""
    fork_json = json.dumps(
        {"action": "fork", "sub_question": "sub question?", "reasoning": "deeper"}
    )
    child_converge = json.dumps(
        {"action": "converge", "reasoning": "child done"}
    )
    child_verdict = json.dumps(
        {
            "summary": "sub conclusion",
            "confidence": "medium",
            "key_facts": [],
            "key_risks": [],
            "key_values": [],
            "mitigations": [],
            "intuition_summary": "",
            "blue_hat_ruling": "OK",
            "next_actions": [],
        }
    )
    parent_converge = json.dumps(
        {"action": "converge", "reasoning": "done"}
    )
    parent_verdict = json.dumps(
        {
            "summary": "main conclusion",
            "confidence": "high",
            "key_facts": [],
            "key_risks": [],
            "key_values": [],
            "mitigations": [],
            "intuition_summary": "",
            "blue_hat_ruling": "OK",
            "next_actions": [],
        }
    )
    responses = [fork_json, child_converge, child_verdict, parent_converge, parent_verdict]
    llm = MockLLM(responses)
    bus = EventBus()
    collector = EventCollector()
    bus.subscribe(collector)

    orch = Orchestrator(llm, [_persona()], _config(), bus)
    await orch.run("main question")

    assert collector.has(EventType.FORK_CREATED)
    assert collector.has(EventType.SUB_CONCLUSION)
    assert len(orch.tree.root.children) == 1
    assert orch.tree.root.children[0].question == "sub question?"


@pytest.mark.asyncio
async def test_all_panelists_fail_forces_conclude_without_empty_round():
    discuss_json = json.dumps(
        {"action": "discuss", "hat": "white", "target_personas": ["tester"], "reasoning": "need facts"}
    )
    verdict_json = json.dumps(
        {
            "summary": "Fallback conclusion",
            "confidence": "low",
            "key_facts": [],
            "key_risks": [],
            "key_values": [],
            "mitigations": [],
            "intuition_summary": "",
            "blue_hat_ruling": "No outputs available",
            "next_actions": [],
        }
    )
    llm = MockLLM([discuss_json, verdict_json])
    bus = EventBus()
    collector = EventCollector()
    bus.subscribe(collector)

    orch = Orchestrator(llm, [_persona()], _config(), bus)

    async def _fail_panelist(*args, **kwargs):
        raise RuntimeError("panelist failure")

    orch._execute_panelist = _fail_panelist  # type: ignore[method-assign]
    await orch.run("question")

    assert orch.tree.root is not None
    assert orch.tree.root.rounds == []
    assert collector.has(EventType.ERROR)
    assert collector.has(EventType.CONCLUSION)


@pytest.mark.asyncio
async def test_execute_round_keeps_blue_hat_reasoning():
    orch = Orchestrator(MockLLM(), [_persona()], _config(), EventBus())
    node = orch.tree.create_root("question")

    async def _ok_panelist(*args, **kwargs):
        return PanelistOutput(
            persona_id="tester",
            hat=HatColor.WHITE,
            content="W1: fact",
            items=[OutputItem(id="W1", content="fact")],
            raw_content="W1: fact",
            token_usage=_usage(),
            validation_passed=True,
        )

    orch._execute_panelist = _ok_panelist  # type: ignore[method-assign]
    round_ = await orch._execute_round(node, HatColor.WHITE, [_persona()], "need facts")
    assert round_.blue_hat_reasoning == "need facts"


@pytest.mark.asyncio
async def test_fork_does_not_mutate_global_round_limit_on_exception():
    orch = Orchestrator(MockLLM(), [_persona()], _config(max_rounds=4, max_fork_rounds=2), EventBus())
    parent = orch.tree.create_root("question")

    async def _boom(node, *, max_rounds=None):
        assert max_rounds == 2
        raise RuntimeError("child failed")

    orch._run_node = _boom  # type: ignore[method-assign]

    with pytest.raises(RuntimeError, match="child failed"):
        await orch._handle_fork(parent, "sub question")

    assert orch.config.max_rounds == 4


# ── Intervention ───────────────────────────────────────────


@pytest.mark.asyncio
async def test_intervention_queued():
    """Interventions are queued and consumed by blue hat."""
    orch = Orchestrator(MockLLM(), [_persona()], _config(), EventBus())
    await orch.intervene("focus on security risks")
    assert not orch._intervention_queue.empty()


# ── HAT_RULES coverage ────────────────────────────────────


def test_hat_rules_all_colors():
    """All non-blue hat colors have rules defined."""
    for hat in [HatColor.WHITE, HatColor.RED, HatColor.BLACK, HatColor.YELLOW, HatColor.GREEN]:
        assert hat in _HAT_RULES
        assert len(_HAT_RULES[hat]) > 0
