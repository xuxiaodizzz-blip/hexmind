"""Tests for hexmind.models — serialization, defaults, and validation."""

import time

import pytest

from hexmind.models import (
    HAT_CONSTRAINTS,
    ContextCheckResult,
    DecisionSummary,
    DegradationLevel,
    DiscussionConfig,
    Dissent,
    EvidenceItem,
    HatColor,
    HatConstraint,
    InteractionMode,
    LLMResponse,
    NodeStatus,
    OutputItem,
    PanelistOutput,
    Persona,
    PersonaTemperature,
    Round,
    TokenPricing,
    TokenUsage,
    TreeNode,
    Verdict,
)


# ── HatColor & HatConstraint ──────────────────────────────────────────

class TestHat:
    def test_hat_color_values(self):
        assert set(HatColor) == {
            HatColor.WHITE, HatColor.RED, HatColor.BLACK,
            HatColor.YELLOW, HatColor.GREEN,
        }

    def test_hat_constraints_cover_all_colors(self):
        for color in HatColor:
            assert color in HAT_CONSTRAINTS

    def test_white_hat_has_prohibited_patterns(self):
        c = HAT_CONSTRAINTS[HatColor.WHITE]
        assert len(c.prohibited_patterns) > 0
        assert c.required_format == r"^W\d+:"

    def test_red_hat_max_sentences(self):
        c = HAT_CONSTRAINTS[HatColor.RED]
        assert c.max_sentences == 3

    def test_black_hat_references_white(self):
        c = HAT_CONSTRAINTS[HatColor.BLACK]
        assert c.references_required == "white"

    def test_green_hat_references_black(self):
        c = HAT_CONSTRAINTS[HatColor.GREEN]
        assert c.references_required == "black"


# ── Persona ────────────────────────────────────────────────────────────

class TestPersona:
    def test_persona_creation(self):
        p = Persona(
            id="backend-eng",
            name="Backend Engineer",
            domain="tech",
            description="Expert in server-side architecture",
        )
        assert p.display_name == "Backend Engineer (tech)"

    def test_persona_invalid_id(self):
        with pytest.raises(Exception):
            Persona(
                id="INVALID ID!",
                name="Bad",
                domain="tech",
                description="Bad id",
            )

    def test_persona_defaults(self):
        p = Persona(id="test", name="T", domain="general", description="D")
        assert p.temperature.white == 0.3
        assert p.temperature.green == 0.8
        assert p.prompt == ""
        assert p.system_prompt_suffix == ""

    def test_persona_roundtrip(self):
        p = Persona(
            id="cfo",
            name="CFO",
            domain="business",
            description="Financial officer",
        )
        data = p.model_dump()
        p2 = Persona.model_validate(data)
        assert p2 == p

    def test_persona_ignores_legacy_hat_preferences(self):
        p = Persona.model_validate(
            {
                "id": "legacy-hats",
                "name": "Legacy Hats",
                "domain": "general",
                "description": "D",
                "hat_preferences": {
                    "white": {"focus": ["facts"], "max_items": 3}
                },
            }
        )
        assert p.hat_preferences == {}

    def test_persona_accepts_legacy_prompt_field(self):
        p = Persona.model_validate(
            {
                "id": "legacy",
                "name": "Legacy",
                "domain": "general",
                "description": "D",
                "system_prompt_suffix": "legacy prompt",
            }
        )
        assert p.prompt == "legacy prompt"
        assert p.system_prompt_suffix == "legacy prompt"


# ── Round / OutputItem / PanelistOutput ─────────────────────────────────

class TestRound:
    def _make_output(self) -> PanelistOutput:
        return PanelistOutput(
            persona_id="backend-eng",
            hat=HatColor.WHITE,
            content="W1: Python 3.11+ required",
            items=[OutputItem(id="W1", content="Python 3.11+ required")],
            raw_content="W1: Python 3.11+ required",
            token_usage=TokenUsage(input_tokens=100, output_tokens=50, total_tokens=150),
            validation_passed=True,
        )

    def test_panelist_output_creation(self):
        o = self._make_output()
        assert o.hat == HatColor.WHITE
        assert o.retry_count == 0

    def test_round_creation(self):
        r = Round(
            number=1,
            hat=HatColor.WHITE,
            blue_hat_reasoning="Starting with facts",
            outputs=[self._make_output()],
            timestamp=time.time(),
        )
        assert r.number == 1
        assert len(r.outputs) == 1

    def test_round_roundtrip(self):
        r = Round(
            number=2,
            hat=HatColor.BLACK,
            blue_hat_reasoning="Time for risks",
            outputs=[],
            timestamp=1234567890.0,
        )
        data = r.model_dump()
        r2 = Round.model_validate(data)
        assert r2.hat == HatColor.BLACK


# ── TreeNode / Verdict / DecisionSummary ────────────────────────────────

class TestTree:
    def test_tree_node_defaults(self):
        n = TreeNode(question="Should we use K8s?")
        assert n.status == NodeStatus.ACTIVE
        assert n.depth == 0
        assert n.id.startswith("node_")
        assert n.verdict is None

    def test_tree_node_with_children(self):
        parent = TreeNode(question="Main question")
        child = TreeNode(question="Sub question", depth=1, parent_id=parent.id)
        parent.children.append(child)
        assert len(parent.children) == 1
        assert parent.children[0].parent_id == parent.id

    def test_verdict_creation(self):
        v = Verdict(
            summary="Use K8s for production",
            confidence="high",
            key_facts=["W1: Team has K8s experience"],
            key_risks=["B1: Complexity overhead"],
            key_values=["Y1: Scalability"],
            mitigations=["G1: Start with managed K8s"],
            intuition_summary="Team feels positive",
            blue_hat_ruling="Consensus reached",
            next_actions=["Set up GKE cluster"],
        )
        assert v.partial is False

    def test_decision_summary_defaults(self):
        ds = DecisionSummary(
            question="Use K8s?",
            decision="Yes",
            reasoning="Team ready",
            confidence="high",
        )
        assert ds.outcome == "pending"
        assert ds.dissents == []
        assert ds.evidence == []

    def test_decision_summary_with_evidence(self):
        ds = DecisionSummary(
            question="Q",
            decision="D",
            reasoning="R",
            confidence="medium",
            evidence=[
                EvidenceItem(id="W1", content="Fact", source_type="domain"),
            ],
            dissents=[
                Dissent(
                    persona_id="cfo",
                    position="Too expensive",
                    reasoning="Budget constraints",
                    evidence_refs=["W1"],
                ),
            ],
        )
        assert len(ds.evidence) == 1
        assert ds.dissents[0].persona_id == "cfo"


# ── Config ──────────────────────────────────────────────────────────────

class TestConfig:
    def test_discussion_config_defaults(self):
        c = DiscussionConfig()
        assert c.max_rounds == 12
        assert c.token_budget == 50_000
        assert c.locale == "zh"
        assert c.default_model == "gpt-4o"

    def test_interaction_mode_default(self):
        m = InteractionMode()
        assert m.mode == "auto"

    def test_degradation_level_default(self):
        d = DegradationLevel()
        assert d.level == "normal"


# ── LLM models ──────────────────────────────────────────────────────────

class TestLLM:
    def test_token_usage(self):
        u = TokenUsage(input_tokens=10, output_tokens=20, total_tokens=30)
        assert u.total_tokens == 30

    def test_token_pricing(self):
        p = TokenPricing(input_per_million=2.5, output_per_million=10.0)
        assert p.input_per_million == 2.5

    def test_llm_response(self):
        r = LLMResponse(
            content="Hello",
            usage=TokenUsage(),
            model="gpt-4o",
        )
        assert r.finish_reason == "stop"

    def test_context_check_result(self):
        c = ContextCheckResult(
            fits=True,
            prompt_tokens=5000,
            context_limit=128000,
            headroom=123000,
        )
        assert c.needs_compression is False
