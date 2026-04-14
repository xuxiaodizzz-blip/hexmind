"""Tests for engine/compressor.py — context compression."""

import time

import pytest

from hexmind.engine.compressor import LLMLinguaCompressor
from hexmind.models.hat import HatColor
from hexmind.models.llm import TokenUsage
from hexmind.models.round import OutputItem, PanelistOutput, Round
from hexmind.models.tree import TreeNode


def _make_round(hat: HatColor, items: list[tuple[str, str]], refs: list[list[str]] | None = None) -> Round:
    """Create a round with given items: list of (id, content)."""
    if refs is None:
        refs = [[] for _ in items]
    output_items = [
        OutputItem(id=item_id, content=content, references=ref)
        for (item_id, content), ref in zip(items, refs)
    ]
    output = PanelistOutput(
        persona_id="p1",
        hat=hat,
        content="\n".join(f"{it.id}: {it.content}" for it in output_items),
        items=output_items,
        raw_content="",
        token_usage=TokenUsage(input_tokens=100, output_tokens=50, total_tokens=150),
        validation_passed=True,
    )
    return Round(number=1, hat=hat, blue_hat_reasoning="test", outputs=[output], timestamp=time.time())


def _count_tokens_fake(text: str) -> int:
    """Fake token counter: ~1 token per 2 chars."""
    return max(1, len(text) // 2)


class TestNoCompression:
    @pytest.mark.asyncio
    async def test_few_rounds_returns_empty(self):
        """With <= KEEP_RECENT_ROUNDS, no compression needed."""
        node = TreeNode(question="q", rounds=[
            _make_round(HatColor.WHITE, [("W1", "fact A")]),
            _make_round(HatColor.BLACK, [("B1", "risk X")]),
        ])
        comp = LLMLinguaCompressor()
        result = await comp.compress(node, _count_tokens_fake)
        assert result == ""

    @pytest.mark.asyncio
    async def test_exactly_keep_rounds_returns_empty(self):
        node = TreeNode(question="q", rounds=[
            _make_round(HatColor.WHITE, [("W1", "a")]),
            _make_round(HatColor.BLACK, [("B1", "b")]),
            _make_round(HatColor.GREEN, [("G1", "c")]),
        ])
        comp = LLMLinguaCompressor()
        assert comp.KEEP_RECENT_ROUNDS == 3
        result = await comp.compress(node, _count_tokens_fake)
        assert result == ""


class TestStructuredPrompt:
    def test_builds_tags(self):
        rounds = [
            _make_round(HatColor.WHITE, [("W1", "数据显示增长"), ("W2", "用户量 500")]),
        ]
        comp = LLMLinguaCompressor()
        prompt = comp._build_structured_prompt(rounds)
        assert "<llmlingua, compress=False>W1:</llmlingua>" in prompt
        assert "<llmlingua, compress=False>W2:</llmlingua>" in prompt
        assert "数据显示增长" in prompt

    def test_protects_references(self):
        rounds = [
            _make_round(
                HatColor.BLACK,
                [("B1", "风险")],
                refs=[["W1", "W2"]],
            ),
        ]
        comp = LLMLinguaCompressor()
        prompt = comp._build_structured_prompt(rounds)
        assert "B1 (ref W1, W2):" in prompt
        assert "compress=False" in prompt


class TestFallbackTruncation:
    @pytest.mark.asyncio
    async def test_truncation_fallback(self):
        """When llmlingua is unavailable, falls back to simple truncation."""
        # Create more than KEEP_RECENT_ROUNDS
        rounds = [
            _make_round(HatColor.WHITE, [("W1", "A" * 200)]),
            _make_round(HatColor.BLACK, [("B1", "B" * 200)]),
            _make_round(HatColor.YELLOW, [("Y1", "C" * 200)]),
            _make_round(HatColor.GREEN, [("G1", "D" * 200)]),
            _make_round(HatColor.WHITE, [("W2", "E" * 200)]),
        ]
        node = TreeNode(question="q", rounds=rounds)

        comp = LLMLinguaCompressor()
        comp._available = False  # force fallback

        result = await comp.compress(node, _count_tokens_fake, target_token=50)
        assert len(result) > 0
        assert "截断" in result or len(result) <= 200

    def test_simple_truncate_short_text(self):
        comp = LLMLinguaCompressor()
        result = comp._simple_truncate("short text", target_token=100)
        assert result == "short text"

    def test_simple_truncate_strips_tags(self):
        comp = LLMLinguaCompressor()
        tagged = '<llmlingua, compress=False>W1:</llmlingua><llmlingua, rate=0.4> content</llmlingua>'
        result = comp._simple_truncate(tagged, target_token=100)
        assert "<llmlingua" not in result
        assert "W1:" in result


class TestEmptyRounds:
    @pytest.mark.asyncio
    async def test_empty_items_returns_empty(self):
        """Rounds with no items produce no structured prompt."""
        rounds = [
            Round(
                number=i, hat=HatColor.WHITE, blue_hat_reasoning="",
                outputs=[], timestamp=time.time(),
            )
            for i in range(5)
        ]
        node = TreeNode(question="q", rounds=rounds)
        comp = LLMLinguaCompressor()
        comp._available = False
        result = await comp.compress(node, _count_tokens_fake)
        assert result == ""
