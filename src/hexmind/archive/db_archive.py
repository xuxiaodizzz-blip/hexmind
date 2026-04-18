"""Database-backed archive backend (Phase 5)."""

from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from hexmind.archive.backend import (
    DiscussionRecord,
    DiscussionSummary,
    SearchFilters,
)
from hexmind.archive.repository import DiscussionRepository


class DBArchive:
    """ArchiveBackend implementation using PostgreSQL via SQLAlchemy."""

    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self._session_factory = session_factory

    async def save_discussion(self, record: DiscussionRecord) -> str:
        async with self._session_factory() as session:
            repo = DiscussionRepository(session)
            disc = await repo.create(
                question=record.question,
                config=record.config,
                model_used=record.model_used,
                discussion_locale=record.discussion_locale,
            )
            # Persist all remaining fields from DiscussionRecord
            if record.status:
                disc.status = record.status
            if record.verdict:
                disc.verdict = record.verdict
            if record.confidence:
                disc.confidence = record.confidence
            disc.total_tokens = record.total_tokens
            disc.total_cost_usd = record.total_cost_usd
            if record.duration_seconds is not None:
                disc.duration_seconds = record.duration_seconds
            if record.completed_at:
                from datetime import datetime, timezone
                try:
                    disc.completed_at = datetime.fromisoformat(record.completed_at)
                except (ValueError, TypeError):
                    pass
            if record.tags:
                await repo.set_tags(disc.id, record.tags)
            await session.commit()
            return disc.id

    async def get_discussion(self, discussion_id: str) -> DiscussionRecord | None:
        async with self._session_factory() as session:
            repo = DiscussionRepository(session)
            disc = await repo.get_by_id(discussion_id)
            if disc is None:
                return None
            return DiscussionRecord(
                id=disc.id,
                question=disc.question,
                status=disc.status,
                config=disc.config,
                verdict=disc.verdict,
                confidence=disc.confidence,
                total_tokens=disc.total_tokens,
                total_cost_usd=disc.total_cost_usd,
                model_used=disc.model_used,
                discussion_locale=disc.discussion_locale,
                created_at=disc.created_at.isoformat() if disc.created_at else "",
                completed_at=(
                    disc.completed_at.isoformat() if disc.completed_at else None
                ),
                duration_seconds=disc.duration_seconds,
                tags=[t.tag for t in disc.tags],
            )

    async def search(self, filters: SearchFilters) -> list[DiscussionSummary]:
        async with self._session_factory() as session:
            repo = DiscussionRepository(session)
            discs = await repo.search(
                filters.query,
                persona=filters.persona,
                hat=filters.hat,
                tag=filters.tag,
                limit=filters.limit,
            )
            return [self._to_summary(d) for d in discs]

    async def list_recent(
        self, limit: int = 50, offset: int = 0
    ) -> list[DiscussionSummary]:
        async with self._session_factory() as session:
            repo = DiscussionRepository(session)
            discs = await repo.list_all(limit=limit, offset=offset)
            return [self._to_summary(d) for d in discs]

    async def delete(self, discussion_id: str) -> bool:
        async with self._session_factory() as session:
            repo = DiscussionRepository(session)
            result = await repo.delete(discussion_id)
            await session.commit()
            return result

    @staticmethod
    def _to_summary(disc) -> DiscussionSummary:
        return DiscussionSummary(
            id=disc.id,
            question=disc.question,
            status=disc.status,
            confidence=disc.confidence,
            created_at=disc.created_at.isoformat() if disc.created_at else "",
            tags=[t.tag for t in disc.tags] if disc.tags else [],
        )
