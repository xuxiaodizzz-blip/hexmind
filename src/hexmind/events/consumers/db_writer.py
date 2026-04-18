"""DBWriter: persist discussion events to database (Phase 5)."""

from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from hexmind.archive.repository import DiscussionRepository, TreeRepository
from hexmind.events.types import (
    BlueHatDecisionPayload,
    ConclusionPayload,
    DiscussionCancelledPayload,
    DiscussionStartedPayload,
    Event,
    EventType,
    ForkCreatedPayload,
    PanelistOutputPayload,
)


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
        payload = event.payload_as(DiscussionStartedPayload)
        if payload is None:
            return

        actor_context = payload.actor_context
        runtime_snapshot = payload.runtime_config_snapshot
        disc = await disc_repo.create(
            question=payload.question,
            config={
                "request_config_snapshot": payload.request_config_snapshot,
                "runtime_config_snapshot": runtime_snapshot,
                "migration_metadata": payload.migration_metadata,
            },
            model_used=(
                runtime_snapshot.get("resolved_model_slug")
                or payload.resolved_model_slug
            ),
            discussion_locale=runtime_snapshot.get(
                "discussion_locale",
                payload.discussion_locale or "zh",
            ),
            user_id=actor_context.user_id,
            team_id=actor_context.team_id,
        )
        self._discussion_id = disc.id

        # Create root tree node
        tree_repo = TreeRepository(session)
        root_node_id = payload.root_node_id or "root"
        node = await tree_repo.create_node(
            discussion_id=disc.id,
            question=payload.question,
            depth=0,
        )
        self._node_map[root_node_id] = node.id

    async def _handle_blue_hat(self, session: AsyncSession, event: Event) -> None:
        if not self._discussion_id:
            return
        payload = event.payload_as(BlueHatDecisionPayload)
        if payload is None:
            return
        tree_repo = TreeRepository(session)
        node_id = payload.node_id or "root"
        db_node_id = self._node_map.get(node_id)
        if not db_node_id:
            return

        round_number = payload.round
        hat = payload.hat.value if payload.hat else "white"
        reasoning = payload.reasoning

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
        payload = event.payload_as(PanelistOutputPayload)
        if payload is None:
            return
        tree_repo = TreeRepository(session)
        node_id = payload.node_id or "root"
        round_number = payload.round
        key = f"{node_id}:{round_number}"
        db_round_id = self._round_map.get(key)
        if not db_round_id:
            return

        items = [item.model_dump(mode="json") for item in payload.items]
        items_json = [
            {"id": i.get("id", ""), "content": i.get("content", ""), "references": i.get("references", [])}
            for i in items
        ]
        token_usage = payload.token_usage.model_dump(mode="json")

        await tree_repo.create_panelist_output(
            round_id=db_round_id,
            persona_id=payload.persona_id,
            hat=payload.hat.value if payload.hat else "",
            content=payload.content,
            raw_content=payload.raw_content,
            items=items_json,
            token_usage=token_usage,
            validation_passed=payload.validation_passed,
            validation_violations=payload.validation_violations,
            retry_count=payload.retry_count,
        )

    async def _handle_fork(self, session: AsyncSession, event: Event) -> None:
        if not self._discussion_id:
            return
        payload = event.payload_as(ForkCreatedPayload)
        if payload is None:
            return
        tree_repo = TreeRepository(session)
        parent_node_id = payload.parent_node_id or "root"
        db_parent_id = self._node_map.get(parent_node_id)

        child_node_id = payload.node_id
        node = await tree_repo.create_node(
            discussion_id=self._discussion_id,
            question=payload.question,
            depth=payload.depth,
            parent_id=db_parent_id,
        )
        self._node_map[child_node_id] = node.id

    async def _handle_conclusion(self, session: AsyncSession, event: Event) -> None:
        if not self._discussion_id:
            return
        disc_repo = DiscussionRepository(session)

        if event.type == EventType.CONCLUSION:
            payload = event.payload_as(ConclusionPayload)
            if payload is None:
                return
            verdict = {
                "summary": payload.summary,
                "confidence": payload.confidence,
                "key_facts": payload.key_facts,
                "key_risks": payload.key_risks,
                "key_values": payload.key_values,
                "mitigations": payload.mitigations,
                "next_actions": payload.next_actions,
                "blue_hat_ruling": payload.blue_hat_ruling,
            }
            partial = payload.partial
            status = "converged" if not partial else "partial"
            token_usage = payload.token_usage
            confidence = payload.confidence
            duration_seconds = payload.duration_seconds
        else:
            payload = event.payload_as(DiscussionCancelledPayload)
            if payload is None:
                return
            verdict = {
                "summary": payload.summary,
                "confidence": payload.confidence,
                "key_facts": payload.key_facts,
                "key_risks": payload.key_risks,
                "key_values": payload.key_values,
                "mitigations": payload.mitigations,
                "next_actions": payload.next_actions,
                "blue_hat_ruling": payload.blue_hat_ruling,
                "partial": True,
            }
            status = "cancelled"
            token_usage = payload.token_usage
            confidence = payload.confidence
            duration_seconds = None

        await disc_repo.update_status(
            self._discussion_id,
            status=status,
            verdict=verdict,
            confidence=confidence,
            total_tokens=token_usage.total_tokens,
            total_cost_usd=event.data.get("token_usage", {}).get("total_cost_usd"),
            duration_seconds=duration_seconds,
        )
