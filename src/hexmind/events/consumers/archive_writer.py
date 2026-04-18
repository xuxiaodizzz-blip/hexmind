"""ArchiveWriter: persist discussion events to disk."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

import yaml
from slugify import slugify

from hexmind.events.types import (
    BlueHatDecisionPayload,
    ConclusionPayload,
    DiscussionCancelledPayload,
    DiscussionStartedPayload,
    Event,
    EventType,
    ForkCreatedPayload,
    PanelistOutputPayload,
    SubConclusionPayload,
)
from hexmind.models.tree import DecisionSummary, EvidenceItem


class ArchiveWriter:
    """Listens to events and writes structured archive files on conclusion."""

    def __init__(self, archive_dir: str = "discussion_archive") -> None:
        self.archive_dir = Path(archive_dir)
        self._discussion_dir: Path | None = None
        self._events: list[Event] = []
        self._meta: dict[str, object] = {}
        self._finalized = False

    async def on_event(self, event: Event) -> None:
        self._events.append(event)

        if event.type == EventType.DISCUSSION_STARTED:
            self._init_archive(event)
            return

        if event.type == EventType.PANELIST_OUTPUT:
            payload = event.payload_as(PanelistOutputPayload)
            if payload is not None:
                self._meta["rounds"] = max(int(self._meta.get("rounds", 0)), payload.round)
            return

        if event.type == EventType.FORK_CREATED:
            payload = event.payload_as(ForkCreatedPayload)
            if payload is not None:
                self._meta["forks"] = int(self._meta.get("forks", 0)) + 1
            return

        if event.type not in (EventType.CONCLUSION, EventType.DISCUSSION_CANCELLED):
            return

        if self._finalized:
            return
        self._finalized = True

        terminal = self._extract_terminal_payload(event)
        if terminal is None:
            return

        if isinstance(terminal, DiscussionCancelledPayload):
            self._meta["status"] = "cancelled"
        else:
            self._meta["status"] = "partial" if terminal.partial else "completed"
        self._meta["verdict"] = terminal.summary
        self._meta["confidence"] = terminal.confidence

        await self._write_files()

    def _init_archive(self, event: Event) -> None:
        payload = event.payload_as(DiscussionStartedPayload)
        if payload is None:
            return

        date = datetime.now(tz=timezone.utc).strftime("%Y-%m-%d")
        question_slug = slugify(payload.question or "untitled")[:40]
        unique_suffix = uuid4().hex[:8]

        self._discussion_dir = self.archive_dir / f"{date}_{question_slug}_{unique_suffix}"
        self._discussion_dir.mkdir(parents=True, exist_ok=True)

        self._meta = {
            "question": payload.question,
            "personas": payload.persona_ids,
            "created_at": datetime.now(tz=timezone.utc).isoformat(),
            "status": "in_progress",
            "rounds": 0,
            "forks": 0,
            "hats_used": [],
            "request_config_snapshot": payload.request_config_snapshot,
            "runtime_config_snapshot": payload.runtime_config_snapshot,
            "migration_metadata": payload.migration_metadata,
        }
        if payload.actor_context.user_id:
            self._meta["user_id"] = payload.actor_context.user_id
        if payload.actor_context.team_id:
            self._meta["team_id"] = payload.actor_context.team_id

    async def _write_files(self) -> None:
        if self._discussion_dir is None:
            return

        meta_path = self._discussion_dir / "meta.yaml"
        meta_path.write_text(
            yaml.dump(self._meta, allow_unicode=True, default_flow_style=False),
            encoding="utf-8",
        )

        discussion_path = self._discussion_dir / "discussion.md"
        discussion_path.write_text(self._render_discussion_markdown(), encoding="utf-8")

        summary_path = self._discussion_dir / "decision_summary.json"
        summary_path.write_text(
            self._extract_decision_summary().model_dump_json(indent=2, ensure_ascii=False),
            encoding="utf-8",
        )

    def _extract_terminal_payload(
        self, event: Event
    ) -> ConclusionPayload | DiscussionCancelledPayload | None:
        if event.type == EventType.CONCLUSION:
            return event.payload_as(ConclusionPayload)
        if event.type == EventType.DISCUSSION_CANCELLED:
            return event.payload_as(DiscussionCancelledPayload)
        return None

    def _extract_decision_summary(self) -> DecisionSummary:
        question = str(self._meta.get("question", ""))
        options: list[str] = []
        benefits: dict[str, list[str]] = {}
        costs: dict[str, list[str]] = {}
        risks: list[str] = []
        evidence: list[EvidenceItem] = []
        terminal: ConclusionPayload | DiscussionCancelledPayload | None = None

        for event in self._events:
            if event.type == EventType.PANELIST_OUTPUT:
                payload = event.payload_as(PanelistOutputPayload)
                if payload is None:
                    continue

                hat = payload.hat.value if payload.hat else ""
                if hat == "green":
                    options.extend(item.content for item in payload.items)
                elif hat == "yellow":
                    for item in payload.items:
                        benefits.setdefault("general", []).append(item.content)
                elif hat == "black":
                    for item in payload.items:
                        costs.setdefault("general", []).append(item.content)
                    risks.extend(item.content for item in payload.items)
                elif hat == "white":
                    for item in payload.items:
                        evidence.append(
                            EvidenceItem(
                                id=item.id,
                                content=item.content,
                                source_type="domain",
                                source_ref=None,
                            )
                        )
                continue

            maybe_terminal = self._extract_terminal_payload(event)
            if maybe_terminal is not None:
                terminal = maybe_terminal

        return DecisionSummary(
            question=question,
            options=options,
            benefits=benefits,
            costs=costs,
            risks=risks,
            evidence=evidence,
            decision=terminal.summary if terminal else "",
            reasoning=terminal.blue_hat_ruling if terminal else "",
            dissents=[],
            confidence=terminal.confidence if terminal and terminal.confidence else "low",
            next_actions=terminal.next_actions if terminal else [],
        )

    def _render_discussion_markdown(self) -> str:
        lines = [f"# 讨论记录: {self._meta.get('question', '')}\n"]
        lines.append(f"- 日期: {str(self._meta.get('created_at', ''))[:10]}")
        lines.append(f"- 参与者: {', '.join(self._meta.get('personas', []))}")
        lines.append(f"- 状态: {self._meta.get('status', 'unknown')}")
        lines.append("---\n")

        current_round = 0
        for event in self._events:
            if event.type == EventType.BLUE_HAT_DECISION:
                payload = event.payload_as(BlueHatDecisionPayload)
                if payload is None:
                    continue

                current_round += 1
                hat = payload.hat.value if payload.hat else "unknown"
                lines.append(f"\n## Round {current_round} - {hat.title()} Hat")
                if payload.reasoning:
                    lines.append(f"*Blue Hat: {payload.reasoning}*\n")
                continue

            if event.type == EventType.PANELIST_OUTPUT:
                payload = event.payload_as(PanelistOutputPayload)
                if payload is None:
                    continue

                lines.append(f"### {payload.persona_id or 'unknown'}")
                lines.append(payload.content)
                lines.append("")
                continue

            if event.type == EventType.FORK_CREATED:
                payload = event.payload_as(ForkCreatedPayload)
                if payload is None:
                    continue
                lines.append(f"\n---\n## FORK: {payload.question}")
                continue

            if event.type == EventType.SUB_CONCLUSION:
                payload = event.payload_as(SubConclusionPayload)
                if payload is None:
                    continue
                lines.append(f"\n### 子结论\n{payload.summary}")
                continue

            terminal = self._extract_terminal_payload(event)
            if terminal is None:
                continue

            title = "最终结论" if event.type == EventType.CONCLUSION else "取消时结论"
            lines.append(f"\n---\n## {title}")
            lines.append(f"**{terminal.summary}**")
            lines.append(f"置信度: {terminal.confidence}")

        return "\n".join(lines)
