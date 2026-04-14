"""QueryPlanner — generate search queries adapted to hat + persona."""

from __future__ import annotations

import json
import logging

from hexmind.knowledge.base import PlannedQuery
from hexmind.llm.base import LLMBackend
from hexmind.models.hat import HatColor
from hexmind.models.persona import Persona

logger = logging.getLogger(__name__)

_HAT_SEARCH_STRATEGY: dict[HatColor, str] = {
    HatColor.WHITE: "搜索客观事实、统计数据和最新研究论文",
    HatColor.BLACK: "搜索风险案例、失败案例和已知问题",
    HatColor.YELLOW: "搜索成功案例、收益数据和积极趋势",
    HatColor.GREEN: "搜索替代方案、创新方法和行业最佳实践",
    HatColor.RED: "",  # Red hat 不需要外部知识
}

# Hats that should trigger knowledge retrieval
KNOWLEDGE_HATS = frozenset({HatColor.WHITE, HatColor.BLACK, HatColor.YELLOW, HatColor.GREEN})

_PLANNER_SYSTEM = """你是检索查询规划器。根据讨论问题、当前帽子和角色，生成 1-3 个搜索查询。

搜索策略: {strategy}
角色领域: {domain}

返回 JSON 数组:
[
  {{"query": "英文搜索词", "target_sources": ["semantic_scholar", "arxiv"], "rationale": "理由"}},
  ...
]

规则:
- 查询词用英文（学术 API 英文效果更好）
- 每个查询 3-8 个关键词
- target_sources 从以下选择: {available_sources}
- 学术问题优先 semantic_scholar / arxiv
- 行业数据优先 web / local_files
- 医学问题优先 semantic_scholar"""


class QueryPlanner:
    """Plan knowledge retrieval queries based on hat color and persona.

    Uses LLM to transform the discussion question into targeted search
    queries for each knowledge source.
    """

    def __init__(self, llm: LLMBackend) -> None:
        self._llm = llm

    async def plan_queries(
        self,
        question: str,
        hat: HatColor,
        persona: Persona,
        context: str,
        available_sources: list[str],
    ) -> list[PlannedQuery]:
        """Generate search queries for the given hat and persona."""
        if hat not in KNOWLEDGE_HATS:
            return []

        strategy = _HAT_SEARCH_STRATEGY.get(hat, "")
        system_prompt = _PLANNER_SYSTEM.format(
            strategy=strategy,
            domain=persona.domain,
            available_sources=", ".join(available_sources),
        )

        user_prompt = (
            f"讨论问题: {question}\n"
            f"角色: {persona.name} ({persona.domain})\n"
            f"帽子: {hat.value}\n"
            f"已有上下文 (前500字): {context[:500]}"
        )

        try:
            response = await self._llm.complete(
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                temperature=0.3,
                max_tokens=500,
                response_format="json",
            )
            data = json.loads(response.content)
            if isinstance(data, list):
                return [PlannedQuery.model_validate(q) for q in data[:3]]
            return []
        except Exception:
            logger.warning("QueryPlanner failed, using fallback", exc_info=True)
            return self._fallback_queries(question, persona, available_sources)

    def _fallback_queries(
        self,
        question: str,
        persona: Persona,
        available_sources: list[str],
    ) -> list[PlannedQuery]:
        """Rule-based fallback when LLM planning fails."""
        # Simple keyword extraction — take the question as-is
        return [
            PlannedQuery(
                query=question,
                target_sources=available_sources[:2],
                rationale="Fallback: direct question search",
            )
        ]
