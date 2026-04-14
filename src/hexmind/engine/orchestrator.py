"""Orchestrator: Blue Hat coordinator — the main discussion engine."""

from __future__ import annotations

import asyncio
import logging
import re
import time
from typing import Any

from pydantic import BaseModel

from hexmind.engine.budget import BudgetTracker, DegradationLevel
from hexmind.engine.compressor import LLMLinguaCompressor
from hexmind.engine.convergence import SemanticConvergenceChecker
from hexmind.engine.decision_tree import DecisionTree
from hexmind.engine.token_accountant import TokenAccountant
from hexmind.engine.validator import OutputValidator
from hexmind.events.bus import EventBus
from hexmind.events.types import Event, EventType
from hexmind.knowledge.base import KnowledgeItem
from hexmind.knowledge.citation import CitationManager
from hexmind.knowledge.hub import KnowledgeHub
from hexmind.knowledge.query_planner import KNOWLEDGE_HATS, QueryPlanner
from hexmind.llm.base import LLMBackend
from hexmind.models.config import DiscussionConfig
from hexmind.models.hat import HatColor
from hexmind.models.persona import Persona
from hexmind.models.round import OutputItem, PanelistOutput, Round
from hexmind.models.tree import NodeStatus, TreeNode, Verdict

logger = logging.getLogger(__name__)


# ── Blue Hat decision model ────────────────────────────────

class BlueHatDecision(BaseModel):
    """Structured output from Blue Hat evaluation."""

    action: str  # "discuss" | "converge" | "fork"
    hat: HatColor | None = None
    target_personas: list[str] = []
    reasoning: str = ""
    sub_question: str | None = None


# ── System prompts ─────────────────────────────────────────

_BLUE_HAT_SYSTEM = """你是六顶帽讨论的 Blue Hat 协调者。你的职责是评估当前讨论状态，决定下一步行动。

当前帽子覆盖: {hat_coverage}
未解决项: {open_gaps}
已完成轮次: {round_count}
降级状态: {degradation}

你必须返回 JSON:
{{
  "action": "discuss" | "converge" | "fork",
  "hat": "white" | "red" | "black" | "yellow" | "green" (仅 action=discuss 时),
  "target_personas": ["persona-id-1", ...] (仅 action=discuss 时),
  "reasoning": "你的理由",
  "sub_question": "子问题" (仅 action=fork 时)
}}

规则:
- 如果缺少 White Hat 事实，先调度 White
- 如果有事实但缺少风险分析，调度 Black
- 如果有风险但缺少解决方案，调度 Green
- 如果已覆盖所有帽子且无新观点，选择 converge
- 如果发现需要深入的子问题，选择 fork
- Red Hat 不超过 1 轮"""

_PANELIST_SYSTEM = """你是 {persona_name}，{persona_desc}

当前你戴着 {hat_color} 帽子。

{hat_rules}

{hat_preference}

{persona_prompt}"""

_HAT_RULES: dict[HatColor, str] = {
    HatColor.WHITE: (
        "White Hat: 只陈述事实和数据。\n"
        "- 每条以 W<编号>: 开头\n"
        "- 不允许使用「我觉得」「可能」「也许」等主观词\n"
        "- 必须标注数据来源"
    ),
    HatColor.RED: (
        "Red Hat: 表达直觉和情感反应。\n"
        "- 以「直觉：」开头\n"
        "- 最多 3 句话\n"
        "- 不需要理性论证"
    ),
    HatColor.BLACK: (
        "Black Hat: 找出风险和问题。\n"
        "- 每条以 B<编号>: 开头\n"
        "- 必须引用 W 编号作为事实依据\n"
        "- 聚焦在最坏情况和现实障碍"
    ),
    HatColor.YELLOW: (
        "Yellow Hat: 找出价值和收益。\n"
        "- 每条以 Y<编号>: 开头\n"
        "- 必须引用 W 编号作为事实依据\n"
        "- 聚焦在最佳情况和潜在收益"
    ),
    HatColor.GREEN: (
        "Green Hat: 提出创意方案。\n"
        "- 每条以 G<编号>: 开头\n"
        "- 必须引用 B 编号说明针对哪个风险\n"
        "- 重点是可执行的行动方案"
    ),
}

_VERDICT_SYSTEM = """基于以下讨论内容，生成结构化决策结论。

返回 JSON:
{{
  "summary": "一句话结论",
  "confidence": "high" | "medium" | "low",
  "key_facts": ["事实1", ...],
  "key_risks": ["风险1", ...],
  "key_values": ["价值1", ...],
  "mitigations": ["缓解措施1", ...],
  "intuition_summary": "红帽直觉摘要",
  "blue_hat_ruling": "协调者最终裁决理由",
  "next_actions": ["行动1", ...]
}}"""


class Orchestrator:
    """Blue Hat coordinator: drives multi-round, multi-hat discussions.

    All output goes through the EventBus — this class never returns results directly.
    """

    def __init__(
        self,
        llm: LLMBackend,
        personas: list[Persona],
        config: DiscussionConfig,
        event_bus: EventBus,
        knowledge_hub: KnowledgeHub | None = None,
        user_id: str | None = None,
        team_id: str | None = None,
    ) -> None:
        self.llm = llm
        self.personas = personas
        self.config = config
        self.bus = event_bus

        self.tree = DecisionTree(config)
        self.validator = OutputValidator()
        self.budget = BudgetTracker(config, event_bus)
        self.convergence = SemanticConvergenceChecker(config)
        self.compressor = LLMLinguaCompressor()
        self.accountant = TokenAccountant(llm.context_limit, config)

        # Knowledge Hub (Phase 4) — optional
        self.knowledge = knowledge_hub
        self.citations = CitationManager() if knowledge_hub else None
        self.query_planner = QueryPlanner(llm) if knowledge_hub else None
        self.user_id = user_id
        self.team_id = team_id
        self.last_run_status: NodeStatus | None = None

        self._cancel_requested = False
        self._intervention_queue: asyncio.Queue[str] = asyncio.Queue()

        # Register budget tracker as event listener
        event_bus.subscribe(self.budget)

    # ── Public API ─────────────────────────────────────────────

    async def run(self, question: str) -> None:
        """Start a full discussion. All output via EventBus."""
        root = self.tree.create_root(question)
        self.last_run_status = None
        try:
            await self.bus.emit(
                Event(
                    type=EventType.DISCUSSION_STARTED,
                    data={
                        "question": question,
                        "personas": [p.id for p in self.personas],
                        "root_node_id": root.id,
                        "config": self.config.model_dump(),
                        "model": self.config.default_model,
                        "locale": self.config.locale,
                        "user_id": self.user_id,
                        "team_id": self.team_id,
                    },
                )
            )

            await self._run_node(root)

            # Generate final verdict
            if root.status == NodeStatus.ACTIVE:
                verdict = await self._generate_verdict(root)
                root.verdict = verdict
                root.status = NodeStatus.CONVERGED
                await self.bus.emit(
                    Event(type=EventType.CONCLUSION, data=verdict.model_dump())
                )
        finally:
            self.last_run_status = root.status
            self._cancel_requested = False

    async def cancel(self) -> None:
        """Request graceful cancellation."""
        self._cancel_requested = True

    async def intervene(self, direction: str) -> None:
        """Queue a human intervention directive."""
        await self._intervention_queue.put(direction)

    def get_status_snapshot(self) -> dict[str, int]:
        """Return discussion metrics for thin API/status consumers."""
        root = self.tree.root
        return {
            "rounds_completed": len(root.rounds) if root else 0,
            "token_used": self.budget.total_tokens,
            "token_budget": self.config.token_budget,
        }

    def has_partial_verdict(self) -> bool:
        """Return whether the current root node ended with a partial verdict."""
        root = self.tree.root
        return bool(root and root.verdict and root.verdict.partial)

    # ── Core loop ──────────────────────────────────────────────

    async def _run_node(self, node: TreeNode) -> None:
        """Drive discussion on a single tree node."""
        while node.status == NodeStatus.ACTIVE:
            # Check cancel
            if self._cancel_requested:
                await self._handle_cancel(node)
                return

            # Check budget
            if self.budget.is_exhausted:
                await self._force_conclude(node, "Token budget exhausted (95%)")
                return

            # Check round limit
            if len(node.rounds) >= self.config.max_rounds:
                await self._force_conclude(node, "Max rounds reached")
                return

            # Blue Hat decides next step
            decision = await self._blue_hat_decide(node)
            await self.bus.emit(
                Event(
                    type=EventType.BLUE_HAT_DECISION,
                    data={
                        "node_id": node.id,
                        "hat": decision.hat.value if decision.hat else None,
                        "action": decision.action,
                        "reasoning": decision.reasoning,
                        "round": len(node.rounds) + 1,
                    },
                )
            )

            if decision.action == "converge":
                break
            elif decision.action == "fork" and decision.sub_question:
                await self._handle_fork(node, decision.sub_question)
            elif decision.action == "discuss" and decision.hat:
                # Get available personas based on budget degradation
                active_personas = self.budget.get_active_personas(self.personas)
                if not active_personas:
                    await self._force_conclude(
                        node,
                        "No active personas remaining under current budget",
                    )
                    return
                target_ids = decision.target_personas or [p.id for p in active_personas]
                targets = [
                    p for p in active_personas if p.id in target_ids
                ]
                if not targets:
                    targets = active_personas

                await self.bus.emit(
                    Event(
                        type=EventType.ROUND_STARTED,
                        data={"round": len(node.rounds) + 1, "hat": decision.hat.value},
                    )
                )

                round_ = await self._execute_round(
                    node,
                    decision.hat,
                    targets,
                    decision.reasoning,
                )
                if not round_.outputs:
                    await self.bus.emit(
                        Event(
                            type=EventType.ERROR,
                            data={
                                "message": "All panelists failed in round",
                                "round": round_.number,
                                "node_id": node.id,
                            },
                        )
                    )
                    await self._force_conclude(
                        node,
                        "All panelists failed in round",
                    )
                    return
                node.rounds.append(round_)

                await self.bus.emit(
                    Event(
                        type=EventType.ROUND_COMPLETED,
                        data={"round": round_.number},
                    )
                )

                # Token-based compression check
                await self._maybe_compress(node)

    # ── Blue Hat ───────────────────────────────────────────────

    async def _blue_hat_decide(self, node: TreeNode) -> BlueHatDecision:
        """Blue Hat evaluates state and decides next action."""
        # Check convergence first
        conv_result = self.convergence.check(node)
        if conv_result.converged:
            return BlueHatDecision(action="converge", reasoning=conv_result.reason)

        # Check for pending intervention
        intervention = None
        if not self._intervention_queue.empty():
            try:
                intervention = self._intervention_queue.get_nowait()
            except asyncio.QueueEmpty:
                pass

        hat_coverage = {r.hat.value for r in node.rounds}
        open_gaps = self.convergence._find_open_items(node)

        system_prompt = _BLUE_HAT_SYSTEM.format(
            hat_coverage=", ".join(sorted(hat_coverage)) or "无",
            open_gaps="; ".join(open_gaps[:5]) or "无",
            round_count=len(node.rounds),
            degradation=self.budget.degradation_level.value,
        )
        if intervention:
            system_prompt += f"\n\n[人工干预]: {intervention}"

        context = self._build_context(node)

        response = await self.llm.complete(
            system_prompt=system_prompt,
            user_prompt=context,
            temperature=0.3,
            response_format="json",
        )
        await self.budget.record_tokens(response.usage.total_tokens)

        try:
            return BlueHatDecision.model_validate_json(response.content)
        except Exception:
            # Fallback: rule-based decision
            return self._rule_based_decision(node, hat_coverage)

    def _rule_based_decision(
        self, node: TreeNode, hat_coverage: set[str]
    ) -> BlueHatDecision:
        """Deterministic fallback when LLM JSON parsing fails."""
        all_ids = [p.id for p in self.personas]

        if "white" not in hat_coverage:
            return BlueHatDecision(
                action="discuss", hat=HatColor.WHITE,
                target_personas=all_ids, reasoning="需要事实数据",
            )
        if "black" not in hat_coverage:
            return BlueHatDecision(
                action="discuss", hat=HatColor.BLACK,
                target_personas=all_ids, reasoning="需要风险分析",
            )
        if "yellow" not in hat_coverage:
            return BlueHatDecision(
                action="discuss", hat=HatColor.YELLOW,
                target_personas=all_ids, reasoning="需要价值分析",
            )
        if "green" not in hat_coverage:
            return BlueHatDecision(
                action="discuss", hat=HatColor.GREEN,
                target_personas=all_ids, reasoning="需要创意方案",
            )
        if "red" not in hat_coverage:
            return BlueHatDecision(
                action="discuss", hat=HatColor.RED,
                target_personas=all_ids, reasoning="需要直觉判断",
            )
        return BlueHatDecision(action="converge", reasoning="所有帽子已覆盖")

    # ── Round execution ────────────────────────────────────────

    async def _execute_round(
        self,
        node: TreeNode,
        hat: HatColor,
        personas: list[Persona],
        blue_hat_reasoning: str,
    ) -> Round:
        """Execute one round: all target personas think with the given hat."""
        tasks = [self._execute_panelist(node, persona, hat) for persona in personas]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        outputs: list[PanelistOutput] = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                logger.warning(
                    "Panelist %s failed in round: %s",
                    personas[i].id,
                    result,
                )
            else:
                outputs.append(result)

        return Round(
            number=len(node.rounds) + 1,
            hat=hat,
            blue_hat_reasoning=blue_hat_reasoning,
            outputs=outputs,
            timestamp=time.time(),
        )

    async def _execute_panelist(
        self, node: TreeNode, persona: Persona, hat: HatColor,
        _retry_count: int = 0,
    ) -> PanelistOutput:
        """Single panelist thinks with one hat."""
        # Knowledge retrieval (Phase 4) — only on first attempt
        knowledge_context = ""
        if (
            self.knowledge
            and self.query_planner
            and self.citations
            and hat in KNOWLEDGE_HATS
            and _retry_count == 0
        ):
            try:
                knowledge_context = await self._retrieve_knowledge(
                    node, persona, hat
                )
            except Exception:
                logger.exception(
                    "Knowledge retrieval failed for persona %s on hat %s",
                    persona.id,
                    hat.value,
                )

        system_prompt = self._build_panelist_prompt(persona, hat, knowledge_context)
        context = self._build_context(node)
        temperature = getattr(persona.temperature, hat.value)

        # Use fallback model if in MINIMAL degradation
        model_override = None
        if self.budget.degradation_level == DegradationLevel.MINIMAL:
            model_override = self.config.fallback_model

        if model_override and model_override != self.llm.model_name:
            # For now, we still use the same LLM but note the intent
            # Full model switching requires LiteLLM Router (Phase 3)
            pass

        response = await self.llm.complete(
            system_prompt=system_prompt,
            user_prompt=context,
            temperature=temperature,
        )

        items = self._parse_output_items(response.content, hat)

        output = PanelistOutput(
            persona_id=persona.id,
            hat=hat,
            content=response.content,
            items=items,
            raw_content=response.content,
            token_usage=response.usage,
            validation_passed=True,
            retry_count=_retry_count,
        )

        # Validate
        validation = self.validator.validate(output, hat, persona)
        if not validation.passed:
            if _retry_count < self.config.max_validation_retries:
                await self.bus.emit(
                    Event(
                        type=EventType.VALIDATION_RESULT,
                        data={
                            "passed": False,
                            "persona_id": persona.id,
                            "violations": [v.description for v in validation.violations],
                        },
                    )
                )
                # Retry with error feedback
                return await self._execute_panelist(
                    node, persona, hat, _retry_count=_retry_count + 1
                )
            else:
                output.validation_passed = False
                output.validation_violations = [
                    v.description for v in validation.violations
                ]

        await self.bus.emit(
            Event(
                type=EventType.PANELIST_OUTPUT,
                data={
                    "node_id": node.id,
                    "persona_id": persona.id,
                    "hat": hat.value,
                    "content": output.content,
                    "raw_content": output.raw_content,
                    "items": [item.model_dump() for item in output.items],
                    "token_usage": output.token_usage.model_dump(),
                    "round": len(node.rounds) + 1,
                    "validation_passed": output.validation_passed,
                    "validation_violations": output.validation_violations,
                    "retry_count": output.retry_count,
                },
            )
        )
        return output

    # ── FORK handling ──────────────────────────────────────────

    async def _handle_fork(self, parent: TreeNode, sub_question: str) -> None:
        """Fork a sub-question as a child node."""
        if not self.tree.can_fork(parent):
            await self.bus.emit(
                Event(
                    type=EventType.ERROR,
                    data={"message": "Cannot fork: depth or width limit reached"},
                )
            )
            return

        child = self.tree.add_child(parent, sub_question)
        await self.bus.emit(
            Event(
                type=EventType.FORK_CREATED,
                data={
                    "parent_node_id": parent.id,
                    "node_id": child.id,
                    "question": sub_question,
                    "depth": child.depth,
                },
            )
        )

        # Run sub-discussion with reduced round limit
        original_max = self.config.max_rounds
        self.config.max_rounds = min(
            self.config.max_fork_rounds, original_max
        )
        try:
            await self._run_node(child)
        finally:
            self.config.max_rounds = original_max

        # Generate sub-conclusion
        if child.status == NodeStatus.ACTIVE:
            sub_verdict = await self._generate_verdict(child)
            child.verdict = sub_verdict
            child.status = NodeStatus.CONVERGED
            await self.bus.emit(
                Event(
                    type=EventType.SUB_CONCLUSION,
                    data={
                        "node_id": child.id,
                        "summary": sub_verdict.summary,
                        "verdict": sub_verdict.model_dump(),
                    },
                )
            )

    # ── Verdict generation ─────────────────────────────────────

    async def _generate_verdict(self, node: TreeNode, partial: bool = False) -> Verdict:
        """Ask LLM to synthesize a structured verdict from discussion."""
        context = self._build_context(node)

        response = await self.llm.complete(
            system_prompt=_VERDICT_SYSTEM,
            user_prompt=context,
            temperature=0.2,
            response_format="json",
        )
        await self.budget.record_tokens(response.usage.total_tokens)

        try:
            data = Verdict.model_validate_json(response.content)
            data.partial = partial
            data.bibliography = self._format_bibliography()
            return data
        except Exception:
            return Verdict(
                summary="无法生成结论",
                confidence="low",
                key_facts=[],
                key_risks=[],
                key_values=[],
                mitigations=[],
                intuition_summary="",
                blue_hat_ruling="讨论数据不足以生成有效结论",
                next_actions=["建议增加讨论轮次或调整参与者"],
                partial=partial,
            )

    # ── Cancel / force conclude ────────────────────────────────

    async def _handle_cancel(self, node: TreeNode) -> None:
        verdict = await self._generate_verdict(node, partial=True)
        node.verdict = verdict
        node.status = NodeStatus.CANCELLED
        await self.bus.emit(
            Event(
                type=EventType.DISCUSSION_CANCELLED,
                data={
                    "reason": "用户取消",
                    "node_id": node.id,
                    **verdict.model_dump(),
                    "partial": True,
                },
            )
        )

    async def _force_conclude(self, node: TreeNode, reason: str) -> None:
        verdict = await self._generate_verdict(node, partial=True)
        node.verdict = verdict
        node.status = NodeStatus.CONVERGED
        await self.bus.emit(
            Event(
                type=EventType.CONCLUSION,
                data={**verdict.model_dump(), "partial": True, "force_reason": reason},
            )
        )

    # ── Knowledge retrieval (Phase 4) ──────────────────────────

    async def _retrieve_knowledge(
        self, node: TreeNode, persona: Persona, hat: HatColor
    ) -> str:
        """Retrieve external knowledge and format as citation-annotated context."""
        assert self.knowledge and self.query_planner and self.citations

        queries = await self.query_planner.plan_queries(
            question=node.question,
            hat=hat,
            persona=persona,
            context=self._build_context(node),
            available_sources=self.knowledge.get_available_sources(),
        )
        if not queries:
            return ""

        items = await self.knowledge.search_multi(queries)
        if not items:
            return ""

        lines: list[str] = []
        for item in items[:5]:  # cap at 5 items to manage token budget
            marker = self.citations.cite(item)
            source_label = item.source.replace("_", " ").title()
            lines.append(f"{marker} [{source_label}] {item.title}")
            if item.snippet:
                lines.append(f"   {item.snippet}")
            if item.url:
                lines.append(f"   URL: {item.url}")
            lines.append("")

        return "\n".join(lines)

    def _format_bibliography(self) -> str:
        """Render bibliography from CitationManager, if any citations exist."""
        if self.citations and self.citations.count > 0:
            return self.citations.render_bibliography()
        return ""

    # ── Compression ────────────────────────────────────────────

    async def _maybe_compress(self, node: TreeNode) -> None:
        context_text = self._build_context(node)
        context_tokens = self.llm.count_tokens(context_text)

        if not self.accountant.needs_compression(context_tokens):
            return

        target = self.accountant.compression_target()
        node.compressed_context = await self.compressor.compress(
            node, self.llm.count_tokens, target_token=target
        )
        await self.bus.emit(
            Event(
                type=EventType.CONTEXT_COMPRESSED,
                data={"node_id": node.id, "target_token": target},
            )
        )

    # ── Context building ───────────────────────────────────────

    def _build_context(self, node: TreeNode) -> str:
        """Build user prompt context from discussion history."""
        parts: list[str] = []
        parts.append(f"问题: {node.question}\n")

        # Add tree context (parent/sibling verdicts)
        tree_ctx = self.tree.get_context_for_node(node)
        if tree_ctx:
            parts.append(tree_ctx + "\n")

        # Add compressed early context if available
        if node.compressed_context:
            parts.append(f"[早期讨论摘要]\n{node.compressed_context}\n")
            # Only show recent rounds
            recent = node.rounds[-self.compressor.KEEP_RECENT_ROUNDS :]
        else:
            recent = node.rounds

        # Format rounds
        for r in recent:
            parts.append(f"\n--- Round {r.number} ({r.hat.value} hat) ---")
            for output in r.outputs:
                parts.append(f"[{output.persona_id}]:")
                parts.append(output.content)

        return "\n".join(parts)

    def _build_panelist_prompt(
        self, persona: Persona, hat: HatColor, knowledge_context: str = ""
    ) -> str:
        """Build system prompt for a panelist."""
        hat_pref = persona.hat_preferences.get(hat.value)
        pref_text = ""
        if hat_pref:
            pref_text = f"聚焦方向: {', '.join(hat_pref.focus)}\n每次最多 {hat_pref.max_items} 条"

        prompt = _PANELIST_SYSTEM.format(
            persona_name=persona.name,
            persona_desc=persona.description,
            hat_color=hat.value,
            hat_rules=_HAT_RULES.get(hat, ""),
            hat_preference=pref_text,
            persona_prompt=persona.prompt,
        )

        if knowledge_context:
            prompt += (
                "\n\n[外部知识参考]\n"
                "以下是为你检索到的外部知识，引用时请保留 [N] 编号标记：\n"
                f"{knowledge_context}"
            )

        return prompt

    # ── Output parsing ─────────────────────────────────────────

    @staticmethod
    def _parse_output_items(content: str, hat: HatColor) -> list[OutputItem]:
        """Parse numbered output items from LLM response."""
        prefix_map = {
            HatColor.WHITE: "W",
            HatColor.RED: "",  # Red hat has no numbered items
            HatColor.BLACK: "B",
            HatColor.YELLOW: "Y",
            HatColor.GREEN: "G",
        }
        prefix = prefix_map.get(hat, "")
        if not prefix:
            return []

        items: list[OutputItem] = []
        pattern = rf"({prefix}\d+)\s*[:：]\s*(.*?)(?=(?:{prefix}\d+\s*[:：])|$)"
        matches = re.findall(pattern, content, re.DOTALL)

        for item_id, raw_content in matches:
            text = raw_content.strip()
            # Extract references (W1, B2, etc.)
            references = re.findall(r"[WBYGwbyg]\d+", text)
            # Filter out self-references
            references = [r.upper() for r in references if not r.upper().startswith(prefix)]
            items.append(
                OutputItem(id=item_id, content=text, references=references)
            )

        return items
