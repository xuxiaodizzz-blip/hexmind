"""Context compressor: LLMLingua-2 structured compression with fallback."""

from __future__ import annotations

import logging
from typing import Protocol, runtime_checkable

from hexmind.models.round import Round
from hexmind.models.tree import TreeNode

logger = logging.getLogger(__name__)


@runtime_checkable
class Compressor(Protocol):
    """Protocol so the compression strategy can be swapped."""

    async def compress(
        self,
        node: TreeNode,
        count_tokens: CountTokensFn,
        target_token: int | None = None,
    ) -> str: ...


# Type alias for the token-counting callable (avoids full LLMBackend dep)
CountTokensFn = type(lambda text: 0)  # placeholder for typing


class LLMLinguaCompressor:
    """BERT-level prompt compressor using LLMLingua-2.

    - Zero LLM API cost (local BERT inference)
    - Protects reference IDs (W1:, B2:, G3:) via structured tags
    - Falls back to simple truncation if llmlingua is unavailable
    """

    KEEP_RECENT_ROUNDS: int = 3

    def __init__(
        self,
        model_name: str = "microsoft/llmlingua-2-xlm-roberta-large-meetingbank",
    ) -> None:
        self._model_name = model_name
        self._compressor = None  # lazy-loaded
        self._available: bool | None = None  # None = not yet checked

    async def compress(
        self,
        node: TreeNode,
        count_tokens,
        target_token: int | None = None,
    ) -> str:
        """Compress early rounds of a node, keeping recent rounds intact.

        Args:
            node: The discussion tree node.
            count_tokens: A callable(text) -> int for token counting.
            target_token: Target compressed token count. Defaults to original/3.

        Returns:
            Compressed context string, or "" if no compression needed.
        """
        if len(node.rounds) <= self.KEEP_RECENT_ROUNDS:
            return ""

        early_rounds = node.rounds[: -self.KEEP_RECENT_ROUNDS]
        structured_prompt = self._build_structured_prompt(early_rounds)

        if not structured_prompt.strip():
            return ""

        if target_token is None:
            original_tokens = count_tokens(structured_prompt)
            target_token = max(original_tokens // 3, 200)

        # Try LLMLingua-2
        compressed = self._try_llmlingua(structured_prompt, target_token)
        if compressed is not None:
            return compressed

        # Fallback: simple truncation
        return self._simple_truncate(structured_prompt, target_token)

    # ── Structured prompt building ─────────────────────────────

    @staticmethod
    def _build_structured_prompt(rounds: list[Round]) -> str:
        """Build a prompt with <llmlingua> tags protecting reference IDs."""
        parts: list[str] = []
        for r in rounds:
            for output in r.outputs:
                for item in output.items:
                    # Build header: "W1 (ref B2, B3):" — protected from compression
                    header = item.id
                    if item.references:
                        header += f" (ref {', '.join(item.references)})"
                    header += ":"

                    parts.append(
                        f"<llmlingua, compress=False>{header}</llmlingua>"
                        f"<llmlingua, rate=0.4> {item.content}</llmlingua>"
                    )
        return "\n".join(parts)

    # ── LLMLingua-2 path ──────────────────────────────────────

    def _try_llmlingua(self, structured_prompt: str, target_token: int) -> str | None:
        """Attempt compression via LLMLingua-2. Returns None on failure."""
        if self._available is False:
            return None

        try:
            compressor = self._get_compressor()
            if compressor is None:
                return None
            result = compressor.structured_compress_prompt(
                structured_prompt,
                target_token=target_token,
            )
            return result.get("compressed_prompt", structured_prompt)
        except Exception as exc:
            logger.warning("LLMLingua compression failed: %s", exc)
            self._available = False
            return None

    def _get_compressor(self):
        """Lazy-load the LLMLingua PromptCompressor."""
        if self._compressor is not None:
            return self._compressor
        try:
            from llmlingua import PromptCompressor

            self._compressor = PromptCompressor(
                model_name=self._model_name,
                use_llmlingua2=True,
            )
            self._available = True
            return self._compressor
        except ImportError:
            logger.info("llmlingua not installed; using truncation fallback")
            self._available = False
            return None
        except Exception as exc:
            logger.warning("Failed to load llmlingua model: %s", exc)
            self._available = False
            return None

    # ── Fallback truncation ────────────────────────────────────

    @staticmethod
    def _simple_truncate(text: str, target_token: int) -> str:
        """Simple character-based truncation (no LLM cost).

        Heuristic: ~1.5 tokens per Chinese character, ~1.3 tokens per English word.
        """
        # Strip llmlingua tags for plain text
        import re

        plain = re.sub(r"</?llmlingua[^>]*>", "", text)
        char_limit = int(target_token * 1.5)
        if len(plain) <= char_limit:
            return plain
        return plain[:char_limit] + "\n[...上下文已截断...]"
