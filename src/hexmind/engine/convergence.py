"""Convergence detection: hat coverage + semantic similarity checks."""

from __future__ import annotations

import logging
from typing import Protocol, runtime_checkable

from pydantic import BaseModel

from hexmind.models.config import DiscussionConfig
from hexmind.models.hat import HatColor
from hexmind.models.tree import TreeNode

logger = logging.getLogger(__name__)

# Hat colors required before convergence is even considered
_REQUIRED_HATS = frozenset({HatColor.WHITE, HatColor.BLACK, HatColor.YELLOW, HatColor.GREEN})

# Markers indicating unresolved items
_OPEN_MARKERS = ("需要更多数据", "待确认", "TBD", "TODO")


class ConvergenceResult(BaseModel):
    """Outcome of a convergence check."""

    converged: bool
    reason: str
    similarity: float | None = None  # semantic similarity score if available


@runtime_checkable
class ConvergenceChecker(Protocol):
    """Protocol so the convergence algorithm can be swapped."""

    def check(self, node: TreeNode) -> ConvergenceResult: ...


class SemanticConvergenceChecker:
    """Check whether a discussion node has converged.

    Three signals (all must pass):
    1. Required hat coverage (White, Black, Yellow, Green)
    2. No unresolved open items
    3. Semantic similarity between recent rounds exceeds threshold
       (requires sentence-transformers; falls back to text-overlap heuristic)
    """

    def __init__(self, config: DiscussionConfig) -> None:
        self.config = config
        self._model = None  # lazy-loaded SentenceTransformer

    def check(self, node: TreeNode) -> ConvergenceResult:
        # Signal 1: hat coverage
        coverage = {r.hat for r in node.rounds}
        missing = _REQUIRED_HATS - coverage
        if missing:
            names = ", ".join(h.value for h in sorted(missing, key=lambda h: h.value))
            return ConvergenceResult(converged=False, reason=f"缺少帽子: {names}")

        # Signal 2: open items
        open_items = self._find_open_items(node)
        if open_items:
            return ConvergenceResult(
                converged=False,
                reason=f"未解决项: {'; '.join(open_items[:3])}",
            )

        # Signal 3: content convergence (need at least convergence_consecutive + 1 rounds)
        min_rounds = self.config.convergence_consecutive + 1
        if len(node.rounds) < min_rounds:
            return ConvergenceResult(converged=False, reason="轮次不足")

        similarity = self._compute_similarity(node)
        if similarity is not None and similarity >= self.config.convergence_threshold:
            return ConvergenceResult(
                converged=True,
                reason=f"内容收敛 (similarity={similarity:.2f})",
                similarity=similarity,
            )

        return ConvergenceResult(
            converged=False,
            reason="讨论仍在发展",
            similarity=similarity,
        )

    # ── Signal helpers ─────────────────────────────────────────

    @staticmethod
    def _find_open_items(node: TreeNode) -> list[str]:
        items: list[str] = []
        for r in node.rounds:
            for o in r.outputs:
                for marker in _OPEN_MARKERS:
                    if marker in o.content:
                        items.append(f"{o.persona_id}/{r.hat.value}: {marker}")
        return items

    def _compute_similarity(self, node: TreeNode) -> float | None:
        """Compute overlap between recent rounds and earlier rounds.

        Tries sentence-transformers first; falls back to text-overlap.
        """
        n = self.config.convergence_consecutive
        recent_rounds = node.rounds[-n:]
        earlier_rounds = node.rounds[:-n]

        if not earlier_rounds:
            return None

        recent_texts = self._extract_texts(recent_rounds)
        earlier_texts = self._extract_texts(earlier_rounds)

        if not recent_texts or not earlier_texts:
            return None

        # Try semantic similarity
        score = self._semantic_similarity(recent_texts, earlier_texts)
        if score is not None:
            return score

        # Fallback: text-overlap heuristic
        return self._text_overlap(recent_texts, earlier_texts)

    @staticmethod
    def _extract_texts(rounds) -> list[str]:
        """Extract item content strings from rounds."""
        texts: list[str] = []
        for r in rounds:
            for o in r.outputs:
                for item in o.items:
                    if item.content.strip():
                        texts.append(item.content.strip())
        return texts

    def _semantic_similarity(
        self, recent: list[str], earlier: list[str]
    ) -> float | None:
        """Compute cosine similarity using sentence-transformers (lazy load)."""
        try:
            model = self._get_model()
            if model is None:
                return None

            recent_emb = model.encode(recent, normalize_embeddings=True)
            earlier_emb = model.encode(earlier, normalize_embeddings=True)

            # Average cosine similarity between recent and earlier centroids
            recent_centroid = recent_emb.mean(axis=0)
            earlier_centroid = earlier_emb.mean(axis=0)

            similarity = float(recent_centroid @ earlier_centroid)
            return max(0.0, min(1.0, similarity))
        except Exception:
            logger.debug("sentence-transformers unavailable, using text overlap")
            return None

    def _get_model(self):
        """Lazy-load sentence-transformers model."""
        if self._model is not None:
            return self._model
        try:
            from sentence_transformers import SentenceTransformer

            # Chinese-optimized model; falls back to multilingual
            self._model = SentenceTransformer("BAAI/bge-small-zh-v1.5")
            return self._model
        except ImportError:
            logger.info("sentence-transformers not installed; using text overlap fallback")
            return None
        except Exception:
            logger.warning("Failed to load sentence-transformers model")
            return None

    @staticmethod
    def _text_overlap(recent: list[str], earlier: list[str]) -> float:
        """Simple text overlap heuristic: ratio of recent items found in earlier."""
        # Truncate to first 50 chars for fuzzy matching
        recent_set = {t[:50] for t in recent}
        earlier_set = {t[:50] for t in earlier}
        if not recent_set:
            return 0.0
        overlap = len(recent_set & earlier_set)
        return overlap / len(recent_set)
