"""DBWriter: persist discussion events to database (Phase 5)."""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from hexmind.archive.repository import DiscussionRepository, KnowledgeRepository, TreeRepository
from hexmind.events.types import Event, EventType


class DBWriter:
    """Listens to events and persists discussion data to the database."""

    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self._session_factory = session_factory
        self._discussion_id: str | None = None
        self._node_map: dict[str, str] = {}  # engine node_id → db node_id
        self._round_map: dict[str, str] = {}  # "{node_id}:{round_number}" → db round_id

    async def on_event(self, event: Event) -> None:
        async with self._session_factory() as session:
            if event.type == EventType.DISCUSSION_STARTED:
                await self._handle_started(session, event)
            elif event.type == EventType.BLUE_HAT_DECISION:
                await self._handle_blue_hat(session, event)
            elif event.type == EventType.PANELIST_OUTPUT:
                await self._handle_panelist_output(session, event)
            elif event.type == EventType.FORK_CREATED:
                await self._handle_fork(session, event)
            elif event.type in (EventType.CONCLUSION, EventType.DISCUSSION_CANCELLED):
                await self._handle_conclusion(session, event)
            await session.commit()

    async def _handle_started(self, session: AsyncSession, event: Event) -> None:
        disc_repo = DiscussionRepository(session)
        disc = await disc_repo.create(
            question=event.data.get("question", ""),
            config=event.data.get("config", {}),
            model_used=event.data.get("model", None),
            locale=event.data.get("locale", "zh"),
            user_id=event.data.get("user_id"),
            team_id=event.data.get("team_id"),
        )
        self._discussion_id = disc.id

        # Create root tree node
        tree_repo = TreeRepository(session)
        root_node_id = event.data.get("root_node_id", "root")
        node = await tree_repo.create_node(
            discussion_id=disc.id,
            question=event.data.get("question", ""),
            depth=0,
        )
        self._node_map[root_node_id] = node.id

    async def _handle_blue_hat(self, session: AsyncSession, event: Event) -> None:
        if not self._discussion_id:
            return
        tree_repo = TreeRepository(session)
        node_id = event.data.get("node_id", "root")
        db_node_id = self._node_map.get(node_id)
        if not db_node_id:
            return

        round_number = event.data.get("round", 1)
        hat = event.data.get("hat", "white")
        reasoning = event.data.get("reasoning", "")

        rnd = await tree_repo.create_round(
            tree_node_id=db_node_id,
            round_number=round_number,
            hat=hat,
            blue_hat_reasoning=reasoning,
        )
        key = f"{node_id}:{round_number}"
        self._round_map[key] = rnd.id

    async def _handle_panelist_output(self, session: AsyncSession, event: Event) -> None:
        if not self._discussion_id:
            return
        tree_repo = TreeRepository(session)
        node_id = event.data.get("node_id", "root")
        round_number = event.data.get("round", 1)
        key = f"{node_id}:{round_number}"
        db_round_id = self._round_map.get(key)
        if not db_round_id:
            return

        items = event.data.get("items", [])
        items_json = [
            {"id": i.get("id", ""), "content": i.get("content", ""), "references": i.get("references", [])}
            for i in items
        ]
        token_usage = event.data.get("token_usage", {})

        await tree_repo.create_panelist_output(
            round_id=db_round_id,
            persona_id=event.data.get("persona_id", ""),
            hat=event.data.get("hat", ""),
            content=event.data.get("content", ""),
            raw_content=event.data.get("raw_content", ""),
            items=items_json,
            token_usage=token_usage,
            validation_passed=event.data.get("validation_passed", True),
            validation_violations=event.data.get("validation_violations", []),
            retry_count=event.data.get("retry_count", 0),
        )

    async def _handle_fork(self, session: AsyncSession, event: Event) -> None:
        if not self._discussion_id:
            return
        tree_repo = TreeRepository(session)
        parent_node_id = event.data.get("parent_node_id", "root")
        db_parent_id = self._node_map.get(parent_node_id)

        child_node_id = event.data.get("node_id", "")
        node = await tree_repo.create_node(
            discussion_id=self._discussion_id,
            question=event.data.get("question", ""),
            depth=event.data.get("depth", 1),
            parent_id=db_parent_id,
        )
        self._node_map[child_node_id] = node.id

    async def _handle_conclusion(self, session: AsyncSession, event: Event) -> None:
        if not self._discussion_id:
            return
        disc_repo = DiscussionRepository(session)

        if event.type == EventType.CONCLUSION:
            verdict = {
                "summary": event.data.get("summary", ""),
                "confidence": event.data.get("confidence", ""),
                "key_facts": event.data.get("key_facts", []),
                "key_risks": event.data.get("key_risks", []),
                "key_values": event.data.get("key_values", []),
                "mitigations": event.data.get("mitigations", []),
                "next_actions": event.data.get("next_actions", []),
                "blue_hat_ruling": event.data.get("blue_hat_ruling", ""),
            }
            partial = event.data.get("partial", False)
            status = "converged" if not partial else "partial"
        else:
            verdict = {
                "summary": event.data.get("summary", ""),
                "confidence": event.data.get("confidence", ""),
                "key_facts": event.data.get("key_facts", []),
                "key_risks": event.data.get("key_risks", []),
                "key_values": event.data.get("key_values", []),
                "mitigations": event.data.get("mitigations", []),
                "next_actions": event.data.get("next_actions", []),
                "blue_hat_ruling": event.data.get("blue_hat_ruling", ""),
                "partial": True,
            }
            status = "cancelled"

        token_usage = event.data.get("token_usage", {})
        await disc_repo.update_status(
            self._discussion_id,
            status=status,
            verdict=verdict,
            confidence=event.data.get("confidence"),
            total_tokens=token_usage.get("total_tokens"),
            total_cost_usd=token_usage.get("total_cost_usd"),
            duration_seconds=event.data.get("duration_seconds"),
        )
