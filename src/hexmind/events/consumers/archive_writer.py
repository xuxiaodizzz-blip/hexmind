"""ArchiveWriter: persist discussion events to disk."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

import yaml
from slugify import slugify

from hexmind.events.types import Event, EventType
from hexmind.models.tree import DecisionSummary, EvidenceItem


class ArchiveWriter:
    """Listens to events and writes structured archive files on conclusion."""

    def __init__(self, archive_dir: str = "discussion_archive") -> None:
        self.archive_dir = Path(archive_dir)
        self._discussion_dir: Path | None = None
        self._events: list[Event] = []
        self._meta: dict = {}
        self._finalized: bool = False

    async def on_event(self, event: Event) -> None:
        self._events.append(event)

        if event.type == EventType.DISCUSSION_STARTED:
            self._init_archive(event)
        elif event.type == EventType.PANELIST_OUTPUT:
            self._meta["rounds"] = max(
                self._meta.get("rounds", 0),
                event.data.get("round", 0),
            )
        elif event.type == EventType.FORK_CREATED:
            self._meta["forks"] = self._meta.get("forks", 0) + 1
        elif event.type in (EventType.CONCLUSION, EventType.DISCUSSION_CANCELLED):
            if self._finalized:
                return  # Ignore duplicate terminal events
            self._finalized = True
            if event.type == EventType.DISCUSSION_CANCELLED:
                self._meta["status"] = "cancelled"
                self._meta["verdict"] = event.data.get("summary", "")
                self._meta["confidence"] = event.data.get("confidence", "")
            else:
                partial = event.data.get("partial", False)
                self._meta["status"] = "partial" if partial else "completed"
                self._meta["verdict"] = event.data.get("summary", "")
                self._meta["confidence"] = event.data.get("confidence", "")
            await self._write_files()

    # ── Initialization ─────────────────────────────────────────

    def _init_archive(self, event: Event) -> None:
        date = datetime.now(tz=timezone.utc).strftime("%Y-%m-%d")
        question_slug = slugify(event.data.get("question", "untitled"))[:40]
        unique_suffix = uuid4().hex[:8]
        self._discussion_dir = self.archive_dir / f"{date}_{question_slug}_{unique_suffix}"
        self._discussion_dir.mkdir(parents=True, exist_ok=True)
        self._meta = {
            "question": event.data.get("question", ""),
            "personas": event.data.get("personas", []),
            "created_at": datetime.now(tz=timezone.utc).isoformat(),
            "status": "in_progress",
            "rounds": 0,
            "forks": 0,
            "hats_used": [],
        }
        if event.data.get("user_id"):
            self._meta["user_id"] = event.data["user_id"]
        if event.data.get("team_id"):
            self._meta["team_id"] = event.data["team_id"]

    # ── File writing ───────────────────────────────────────────

    async def _write_files(self) -> None:
        if self._discussion_dir is None:
            return

        # meta.yaml
        meta_path = self._discussion_dir / "meta.yaml"
        meta_path.write_text(
            yaml.dump(self._meta, allow_unicode=True, default_flow_style=False),
            encoding="utf-8",
        )

        # discussion.md
        discussion_path = self._discussion_dir / "discussion.md"
        discussion_path.write_text(
            self._render_discussion_markdown(),
            encoding="utf-8",
        )

        # decision_summary.json
        summary = self._extract_decision_summary()
        summary_path = self._discussion_dir / "decision_summary.json"
        summary_path.write_text(
            summary.model_dump_json(indent=2, ensure_ascii=False),
            encoding="utf-8",
        )

    # ── Decision summary extraction ───────────────────────────

    def _extract_decision_summary(self) -> DecisionSummary:
        question = self._meta.get("question", "")
        options: list[str] = []
        benefits: dict[str, list[str]] = {}
        costs: dict[str, list[str]] = {}
        risks: list[str] = []
        evidence: list[EvidenceItem] = []
        conclusion_event: Event | None = None

        for event in self._events:
            if event.type == EventType.PANELIST_OUTPUT:
                hat = event.data.get("hat", "")
                items = event.data.get("items", [])
                if hat == "green":
                    options.extend(item.get("content", "") for item in items)
                elif hat == "yellow":
                    for item in items:
                        benefits.setdefault("general", []).append(
                            item.get("content", "")
                        )
                elif hat == "black":
                    for item in items:
                        costs.setdefault("general", []).append(
                            item.get("content", "")
                        )
                    risks.extend(item.get("content", "") for item in items)
                elif hat == "white":
                    for item in items:
                        evidence.append(
                            EvidenceItem(
                                id=item.get("id", ""),
                                content=item.get("content", ""),
                                source_type=item.get("source_type", "domain"),
                                source_ref=item.get("source_ref"),
                            )
                        )
            elif event.type in (EventType.CONCLUSION, EventType.DISCUSSION_CANCELLED):
                conclusion_event = event

        return DecisionSummary(
            question=question,
            options=options,
            benefits=benefits,
            costs=costs,
            risks=risks,
            evidence=evidence,
            decision=(
                conclusion_event.data.get("summary", "") if conclusion_event else ""
            ),
            reasoning=(
                conclusion_event.data.get("blue_hat_ruling", "")
                if conclusion_event
                else ""
            ),
            dissents=[],
            confidence=(
                conclusion_event.data.get("confidence", "low")
                if conclusion_event
                else "low"
            ),
            next_actions=(
                conclusion_event.data.get("next_actions", [])
                if conclusion_event
                else []
            ),
        )

    # ── Markdown rendering ─────────────────────────────────────

    def _render_discussion_markdown(self) -> str:
        lines = [f"# 讨论记录: {self._meta.get('question', '')}\n"]
        lines.append(f"- 日期: {self._meta.get('created_at', '')[:10]}")
        lines.append(
            f"- 参与者: {', '.join(self._meta.get('personas', []))}"
        )
        lines.append(f"- 状态: {self._meta.get('status', 'unknown')}")
        lines.append("---\n")

        current_round = 0
        for event in self._events:
            if event.type == EventType.BLUE_HAT_DECISION:
                current_round += 1
                hat = event.data.get("hat") or "unknown"
                reasoning = event.data.get("reasoning", "")
                lines.append(f"\n## Round {current_round} — {hat.title()} Hat")
                lines.append(f"*Blue Hat: {reasoning}*\n")
            elif event.type == EventType.PANELIST_OUTPUT:
                persona = event.data.get("persona_id", "unknown")
                content = event.data.get("content", "")
                lines.append(f"### {persona}")
                lines.append(content)
                lines.append("")
            elif event.type == EventType.FORK_CREATED:
                q = event.data.get("question", "")
                lines.append(f"\n---\n## FORK: {q}")
            elif event.type == EventType.SUB_CONCLUSION:
                summary = event.data.get("summary", "")
                lines.append(f"\n### 子结论\n{summary}")
            elif event.type == EventType.CONCLUSION:
                summary = event.data.get("summary", "")
                confidence = event.data.get("confidence", "")
                lines.append(f"\n---\n## 最终结论")
                lines.append(f"**{summary}**")
                lines.append(f"置信度: {confidence}")
            elif event.type == EventType.DISCUSSION_CANCELLED:
                summary = event.data.get("summary", "")
                confidence = event.data.get("confidence", "")
                lines.append(f"\n---\n## 取消时结论")
                lines.append(f"**{summary}**")
                lines.append(f"置信度: {confidence}")

        return "\n".join(lines)
