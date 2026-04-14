"""Tests for engine/convergence.py — convergence detection."""

import time

from hexmind.engine.convergence import ConvergenceResult, SemanticConvergenceChecker
from hexmind.models.config import DiscussionConfig
from hexmind.models.hat import HatColor
from hexmind.models.llm import TokenUsage
from hexmind.models.round import OutputItem, PanelistOutput, Round
from hexmind.models.tree import TreeNode


def _make_round(hat: HatColor, items_content: list[str], persona_id: str = "p1") -> Round:
    items = [OutputItem(id=f"{hat.value[0].upper()}{i+1}", content=c) for i, c in enumerate(items_content)]
    output = PanelistOutput(
        persona_id=persona_id,
        hat=hat,
        content="\n".join(f"{it.id}: {it.content}" for it in items),
        items=items,
        raw_content="",
        token_usage=TokenUsage(input_tokens=100, output_tokens=50, total_tokens=150),
        validation_passed=True,
    )
    return Round(
        number=1,
        hat=hat,
        blue_hat_reasoning="test",
        outputs=[output],
        timestamp=time.time(),
    )


def _full_coverage_node(extra_rounds: list[Round] | None = None) -> TreeNode:
    """Create a node with all 4 required hats covered."""
    rounds = [
        _make_round(HatColor.WHITE, ["数据点 A", "数据点 B"]),
        _make_round(HatColor.BLACK, ["风险 X 基于 W1", "风险 Y"]),
        _make_round(HatColor.YELLOW, ["收益 A 基于 W1"]),
        _make_round(HatColor.GREEN, ["方案 1 针对 B1"]),
    ]
    if extra_rounds:
        rounds.extend(extra_rounds)
    return TreeNode(question="test question", rounds=rounds)


class TestHatCoverage:
    def test_missing_hats_not_converged(self):
        node = TreeNode(question="q", rounds=[
            _make_round(HatColor.WHITE, ["fact"]),
        ])
        checker = SemanticConvergenceChecker(DiscussionConfig())
        result = checker.check(node)
        assert not result.converged
        assert "缺少帽子" in result.reason

    def test_all_hats_covered(self):
        node = _full_coverage_node()
        checker = SemanticConvergenceChecker(DiscussionConfig())
        result = checker.check(node)
        # Won't converge yet (not enough rounds for similarity), but no "missing hats" error
        assert "缺少帽子" not in result.reason


class TestOpenItems:
    def test_open_markers_block_convergence(self):
        node = _full_coverage_node()
        # Add a round with open marker
        node.rounds.append(
            _make_round(HatColor.WHITE, ["需要更多数据"])
        )
        checker = SemanticConvergenceChecker(DiscussionConfig())
        result = checker.check(node)
        assert not result.converged
        assert "未解决项" in result.reason

    def test_tbd_marker_blocks(self):
        node = _full_coverage_node()
        node.rounds.append(_make_round(HatColor.BLACK, ["TBD 待评估"]))
        checker = SemanticConvergenceChecker(DiscussionConfig())
        result = checker.check(node)
        assert not result.converged
        assert "未解决项" in result.reason


class TestTextOverlap:
    def test_identical_rounds_converge(self):
        """When recent rounds repeat earlier content → convergence."""
        # 4 required hats + 2 repeat rounds (convergence_consecutive=2 default)
        shared_items = ["数据点 A", "数据点 B"]
        extra = [
            _make_round(HatColor.WHITE, shared_items),
            _make_round(HatColor.WHITE, shared_items),
        ]
        node = _full_coverage_node(extra_rounds=extra)
        checker = SemanticConvergenceChecker(DiscussionConfig(
            convergence_threshold=0.5,
            convergence_consecutive=2,
        ))
        result = checker.check(node)
        assert result.converged
        assert result.similarity is not None
        assert result.similarity >= 0.5

    def test_novel_content_does_not_converge(self):
        """Completely different content → no convergence."""
        extra = [
            _make_round(HatColor.WHITE, ["全新观点 X"]),
            _make_round(HatColor.WHITE, ["全新观点 Y"]),
        ]
        node = _full_coverage_node(extra_rounds=extra)
        checker = SemanticConvergenceChecker(DiscussionConfig(
            convergence_threshold=0.8,
            convergence_consecutive=2,
        ))
        result = checker.check(node)
        assert not result.converged

    def test_insufficient_rounds(self):
        """Not enough rounds → not converged."""
        node = _full_coverage_node()  # 4 rounds, need consecutive+1=3 → OK
        checker = SemanticConvergenceChecker(DiscussionConfig(
            convergence_consecutive=5,  # need 6 rounds
        ))
        result = checker.check(node)
        assert not result.converged
        assert "轮次不足" in result.reason


class TestConvergenceResult:
    def test_result_model(self):
        r = ConvergenceResult(converged=True, reason="test", similarity=0.95)
        assert r.converged
        assert r.similarity == 0.95

    def test_result_defaults(self):
        r = ConvergenceResult(converged=False, reason="no")
        assert r.similarity is None
