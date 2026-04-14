"""TokenAccountant: pre-call token checks and compression triggering."""

from __future__ import annotations

from hexmind.models.config import DiscussionConfig
from hexmind.models.llm import ContextCheckResult
from hexmind.models.tree import TreeNode


class TokenAccountant:
    """Calculate token usage before LLM calls and decide when to compress.

    Solves:
    - T1-3: token-based compression trigger (replaces "5 rounds" heuristic)
    - T1-5: pre-call token estimation for concurrent panelist execution
    """

    # Reserve tokens for LLM output generation
    OUTPUT_RESERVE: int = 2000
    # Trigger compression when context exceeds this fraction of available space
    COMPRESSION_THRESHOLD: float = 0.5

    def __init__(self, context_limit: int, config: DiscussionConfig) -> None:
        self._context_limit = context_limit
        self.config = config

    @property
    def available_context(self) -> int:
        """Tokens available for prompt (context_limit minus output reserve)."""
        return max(0, self._context_limit - self.OUTPUT_RESERVE)

    def check_context_fit(
        self,
        system_tokens: int,
        user_tokens: int,
    ) -> ContextCheckResult:
        """Check whether a prompt fits within the context window."""
        total = system_tokens + user_tokens
        available = self.available_context
        headroom = available - total
        return ContextCheckResult(
            fits=total <= available,
            prompt_tokens=total,
            context_limit=self._context_limit,
            headroom=headroom,
            needs_compression=headroom < 0,
        )

    def needs_compression(self, context_tokens: int) -> bool:
        """Token-based compression trigger.

        Returns True when the current context tokens exceed
        COMPRESSION_THRESHOLD of available_context.
        """
        threshold = int(self.available_context * self.COMPRESSION_THRESHOLD)
        return context_tokens > threshold

    def estimate_round_tokens(self, num_personas: int) -> int:
        """Estimate token cost of a full round (all panelists).

        Used to pre-reserve budget before concurrent execution.
        Heuristics: ~800 input + ~600 output + ~200 overhead per panelist.
        """
        avg_per_panelist = 800 + 600 + 200  # input + output + overhead
        return num_personas * avg_per_panelist

    def compression_target(self) -> int:
        """Recommended target token count after compression."""
        return max(200, self.available_context // 3)
