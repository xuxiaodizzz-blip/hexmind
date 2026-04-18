"""Repository: CRUD operations for database-backed archive."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from hexmind.discussion_contract import normalize_discussion_config_snapshot
from hexmind.archive.db_models import (
    CitationDB,
    DiscussionDB,
    DiscussionTagDB,
    InterventionDB,
    KnowledgeItemDB,
    PanelistOutputDB,
    RoundDB,
    TeamDB,
    TeamMemberDB,
    TreeNodeDB,
    UserDB,
)
from hexmind.user_settings_contract import merge_user_settings, normalize_user_settings


# ---------------------------------------------------------------------------
# User
# ---------------------------------------------------------------------------


class UserRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create(
        self,
        *,
        email: str,
        display_name: str,
        password_hash: str,
        settings: dict[str, Any] | None = None,
    ) -> UserDB:
        user = UserDB(
            email=email,
            display_name=display_name,
            password_hash=password_hash,
            settings=normalize_user_settings(settings),
        )
        self.session.add(user)
        await self.session.flush()
        return user

    async def get_by_id(self, user_id: str) -> UserDB | None:
        user = await self.session.get(UserDB, user_id)
        return self._normalize_settings(user)

    async def get_by_email(self, email: str) -> UserDB | None:
        stmt = select(UserDB).where(UserDB.email == email)
        result = await self.session.execute(stmt)
        user = result.scalar_one_or_none()
        return self._normalize_settings(user)

    async def update_last_login(self, user_id: str) -> None:
        user = await self.get_by_id(user_id)
        if user:
            user.last_login_at = datetime.now(timezone.utc)
            await self.session.flush()

    async def update_settings(
        self,
        user_id: str,
        settings_patch: dict[str, Any],
    ) -> dict[str, Any] | None:
        user = await self.get_by_id(user_id)
        if user is None:
            return None

        user.settings = merge_user_settings(user.settings, settings_patch)
        await self.session.flush()
        return dict(user.settings)

    @staticmethod
    def _normalize_settings(user: UserDB | None) -> UserDB | None:
        if user is None:
            return None

        user.settings = normalize_user_settings(user.settings)
        return user


# ---------------------------------------------------------------------------
# Team
# ---------------------------------------------------------------------------


class TeamRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create(self, *, name: str, owner_id: str) -> TeamDB:
        team = TeamDB(name=name, owner_id=owner_id)
        self.session.add(team)
        await self.session.flush()
        # Auto-add owner as member with owner role
        member = TeamMemberDB(team_id=team.id, user_id=owner_id, role="owner")
        self.session.add(member)
        await self.session.flush()
        return team

    async def get_by_id(self, team_id: str) -> TeamDB | None:
        stmt = (
            select(TeamDB)
            .options(
                selectinload(TeamDB.members).selectinload(TeamMemberDB.user)
            )
            .where(TeamDB.id == team_id)
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def list_for_user(self, user_id: str) -> list[TeamDB]:
        stmt = (
            select(TeamDB)
            .options(selectinload(TeamDB.members))
            .join(TeamMemberDB)
            .where(TeamMemberDB.user_id == user_id)
            .order_by(TeamDB.created_at.desc())
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def add_member(
        self, *, team_id: str, user_id: str, role: str = "member"
    ) -> TeamMemberDB:
        member = TeamMemberDB(team_id=team_id, user_id=user_id, role=role)
        self.session.add(member)
        await self.session.flush()
        return member

    async def remove_member(self, *, team_id: str, user_id: str) -> bool:
        stmt = select(TeamMemberDB).where(
            TeamMemberDB.team_id == team_id, TeamMemberDB.user_id == user_id
        )
        result = await self.session.execute(stmt)
        member = result.scalar_one_or_none()
        if member and member.role != "owner":
            await self.session.delete(member)
            await self.session.flush()
            return True
        return False

    async def get_member_role(self, team_id: str, user_id: str) -> str | None:
        stmt = select(TeamMemberDB.role).where(
            TeamMemberDB.team_id == team_id, TeamMemberDB.user_id == user_id
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()


# ---------------------------------------------------------------------------
# Discussion
# ---------------------------------------------------------------------------


class DiscussionRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create(
        self,
        *,
        question: str,
        config: dict,
        user_id: str | None = None,
        team_id: str | None = None,
        model_used: str | None = None,
        discussion_locale: str = "zh",
    ) -> DiscussionDB:
        disc = DiscussionDB(
            question=question,
            config=normalize_discussion_config_snapshot(config),
            user_id=user_id,
            team_id=team_id,
            model_used=model_used,
            discussion_locale=discussion_locale,
        )
        self.session.add(disc)
        await self.session.flush()
        return disc

    async def get_by_id(self, discussion_id: str) -> DiscussionDB | None:
        stmt = (
            select(DiscussionDB)
            .options(
                selectinload(DiscussionDB.tags),
                selectinload(DiscussionDB.tree_nodes),
            )
            .where(DiscussionDB.id == discussion_id)
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def update_status(
        self,
        discussion_id: str,
        *,
        status: str,
        verdict: dict | None = None,
        confidence: str | None = None,
        total_tokens: int | None = None,
        total_cost_usd: float | None = None,
        duration_seconds: float | None = None,
    ) -> None:
        disc = await self.session.get(DiscussionDB, discussion_id)
        if not disc:
            return
        disc.status = status
        if verdict is not None:
            disc.verdict = verdict
        if confidence is not None:
            disc.confidence = confidence
        if total_tokens is not None:
            disc.total_tokens = total_tokens
        if total_cost_usd is not None:
            disc.total_cost_usd = total_cost_usd
        if duration_seconds is not None:
            disc.duration_seconds = duration_seconds
        if status in ("converged", "cancelled", "error"):
            disc.completed_at = datetime.now(timezone.utc)
        await self.session.flush()

    async def list_for_user(
        self,
        user_id: str,
        *,
        team_id: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[DiscussionDB]:
        stmt = select(DiscussionDB).options(selectinload(DiscussionDB.tags))
        if team_id:
            stmt = stmt.where(DiscussionDB.team_id == team_id)
        else:
            stmt = stmt.where(DiscussionDB.user_id == user_id)
        stmt = stmt.order_by(DiscussionDB.created_at.desc()).limit(limit).offset(offset)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def list_all(
        self, *, limit: int = 50, offset: int = 0
    ) -> list[DiscussionDB]:
        stmt = (
            select(DiscussionDB)
            .options(selectinload(DiscussionDB.tags))
            .order_by(DiscussionDB.created_at.desc())
            .limit(min(limit, 100))
            .offset(offset)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def search(
        self,
        query: str,
        *,
        user_id: str | None = None,
        team_id: str | None = None,
        persona: str | None = None,
        hat: str | None = None,
        tag: str | None = None,
        limit: int = 20,
    ) -> list[DiscussionDB]:
        stmt = (
            select(DiscussionDB)
            .options(selectinload(DiscussionDB.tags))
            .distinct()
        )
        if user_id and not team_id:
            stmt = stmt.where(DiscussionDB.user_id == user_id)
        if team_id:
            stmt = stmt.where(DiscussionDB.team_id == team_id)
        if query:
            escaped = query.replace("%", "\\%").replace("_", "\\_")
            stmt = stmt.where(
                DiscussionDB.question.ilike(f"%{escaped}%", escape="\\")
            )
        if tag:
            stmt = stmt.join(DiscussionTagDB).where(DiscussionTagDB.tag == tag)
        if persona or hat:
            stmt = stmt.join(DiscussionDB.tree_nodes).join(TreeNodeDB.rounds)
            if persona or hat:
                stmt = stmt.join(RoundDB.outputs)
            if persona:
                stmt = stmt.where(PanelistOutputDB.persona_id == persona)
            if hat:
                stmt = stmt.where(PanelistOutputDB.hat == hat)
        stmt = stmt.order_by(DiscussionDB.created_at.desc()).limit(limit)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def delete(self, discussion_id: str) -> bool:
        disc = await self.session.get(DiscussionDB, discussion_id)
        if not disc:
            return False
        await self.session.delete(disc)
        await self.session.flush()
        return True

    async def set_tags(self, discussion_id: str, tags: list[str]) -> None:
        # Remove existing
        stmt = select(DiscussionTagDB).where(
            DiscussionTagDB.discussion_id == discussion_id
        )
        result = await self.session.execute(stmt)
        for existing in result.scalars().all():
            await self.session.delete(existing)
        # Add new
        for tag in tags:
            self.session.add(
                DiscussionTagDB(discussion_id=discussion_id, tag=tag)
            )
        await self.session.flush()


# ---------------------------------------------------------------------------
# Tree / Round / Output (write)
# ---------------------------------------------------------------------------


class TreeRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create_node(
        self,
        *,
        discussion_id: str,
        question: str,
        depth: int = 0,
        parent_id: str | None = None,
    ) -> TreeNodeDB:
        node = TreeNodeDB(
            discussion_id=discussion_id,
            question=question,
            depth=depth,
            parent_id=parent_id,
        )
        self.session.add(node)
        await self.session.flush()
        return node

    async def update_node_status(
        self, node_id: str, status: str, *, verdict: dict | None = None
    ) -> None:
        node = await self.session.get(TreeNodeDB, node_id)
        if node:
            node.status = status
            if verdict is not None:
                node.verdict = verdict
            await self.session.flush()

    async def create_round(
        self,
        *,
        tree_node_id: str,
        round_number: int,
        hat: str,
        blue_hat_reasoning: str | None = None,
    ) -> RoundDB:
        rnd = RoundDB(
            tree_node_id=tree_node_id,
            round_number=round_number,
            hat=hat,
            blue_hat_reasoning=blue_hat_reasoning,
        )
        self.session.add(rnd)
        await self.session.flush()
        return rnd

    async def create_panelist_output(
        self,
        *,
        round_id: str,
        persona_id: str,
        hat: str,
        content: str,
        raw_content: str,
        items: list[dict],
        token_usage: dict,
        validation_passed: bool = True,
        validation_violations: list[str] | None = None,
        retry_count: int = 0,
    ) -> PanelistOutputDB:
        output = PanelistOutputDB(
            round_id=round_id,
            persona_id=persona_id,
            hat=hat,
            content=content,
            raw_content=raw_content,
            items=items,
            token_usage=token_usage,
            validation_passed=validation_passed,
            validation_violations=validation_violations or [],
            retry_count=retry_count,
        )
        self.session.add(output)
        await self.session.flush()
        return output

    async def create_intervention(
        self,
        *,
        discussion_id: str,
        type: str,
        content: str,
        user_id: str | None = None,
    ) -> InterventionDB:
        intervention = InterventionDB(
            discussion_id=discussion_id,
            user_id=user_id,
            type=type,
            content=content,
        )
        self.session.add(intervention)
        await self.session.flush()
        return intervention

    async def get_full_tree(self, discussion_id: str) -> list[TreeNodeDB]:
        stmt = (
            select(TreeNodeDB)
            .options(
                selectinload(TreeNodeDB.rounds).selectinload(RoundDB.outputs)
            )
            .where(TreeNodeDB.discussion_id == discussion_id)
            .order_by(TreeNodeDB.depth, TreeNodeDB.created_at)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())


# ---------------------------------------------------------------------------
# Knowledge / Citations
# ---------------------------------------------------------------------------


class KnowledgeRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def upsert_item(
        self,
        *,
        source: str,
        external_id: str,
        title: str,
        snippet: str | None = None,
        url: str | None = None,
        year: int | None = None,
        authors: list[str] | None = None,
        citation_count: int | None = None,
        metadata: dict | None = None,
    ) -> KnowledgeItemDB:
        stmt = select(KnowledgeItemDB).where(
            KnowledgeItemDB.source == source,
            KnowledgeItemDB.external_id == external_id,
        )
        result = await self.session.execute(stmt)
        item = result.scalar_one_or_none()
        if item:
            item.title = title
            if snippet is not None:
                item.snippet = snippet
            if url is not None:
                item.url = url
            if year is not None:
                item.year = year
            if authors is not None:
                item.authors = authors
            if citation_count is not None:
                item.citation_count = citation_count
            if metadata is not None:
                item.metadata_ = metadata
        else:
            item = KnowledgeItemDB(
                source=source,
                external_id=external_id,
                title=title,
                snippet=snippet,
                url=url,
                year=year,
                authors=authors or [],
                citation_count=citation_count,
                metadata_=metadata or {},
            )
            self.session.add(item)
        await self.session.flush()
        return item

    async def create_citation(
        self,
        *,
        panelist_output_id: str,
        knowledge_item_id: str,
        citation_number: int,
    ) -> CitationDB:
        citation = CitationDB(
            panelist_output_id=panelist_output_id,
            knowledge_item_id=knowledge_item_id,
            citation_number=citation_number,
        )
        self.session.add(citation)
        await self.session.flush()
        return citation


# ---------------------------------------------------------------------------
# Analytics
# ---------------------------------------------------------------------------


class AnalyticsRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def summary(
        self,
        *,
        user_id: str | None = None,
        team_id: str | None = None,
    ) -> dict[str, Any]:
        base = select(DiscussionDB)
        if team_id:
            base = base.where(DiscussionDB.team_id == team_id)
        elif user_id:
            base = base.where(DiscussionDB.user_id == user_id)

        # Total discussions
        count_stmt = select(func.count()).select_from(base.subquery())
        total = (await self.session.execute(count_stmt)).scalar() or 0

        # Tokens / cost
        agg_stmt = select(
            func.coalesce(func.sum(DiscussionDB.total_tokens), 0),
            func.coalesce(func.sum(DiscussionDB.total_cost_usd), 0),
        )
        if team_id:
            agg_stmt = agg_stmt.where(DiscussionDB.team_id == team_id)
        elif user_id:
            agg_stmt = agg_stmt.where(DiscussionDB.user_id == user_id)
        agg_row = (await self.session.execute(agg_stmt)).one()
        total_tokens = agg_row[0]
        total_cost = float(agg_row[1])

        # Confidence distribution
        conf_stmt = (
            select(DiscussionDB.confidence, func.count())
            .group_by(DiscussionDB.confidence)
        )
        if team_id:
            conf_stmt = conf_stmt.where(DiscussionDB.team_id == team_id)
        elif user_id:
            conf_stmt = conf_stmt.where(DiscussionDB.user_id == user_id)
        conf_rows = (await self.session.execute(conf_stmt)).all()
        confidence_dist = {row[0] or "unknown": row[1] for row in conf_rows}

        # Hat distribution
        hat_stmt = (
            select(RoundDB.hat, func.count())
            .join(TreeNodeDB)
            .join(DiscussionDB)
            .group_by(RoundDB.hat)
        )
        if team_id:
            hat_stmt = hat_stmt.where(DiscussionDB.team_id == team_id)
        elif user_id:
            hat_stmt = hat_stmt.where(DiscussionDB.user_id == user_id)
        hat_rows = (await self.session.execute(hat_stmt)).all()
        hat_dist = {row[0]: row[1] for row in hat_rows}

        return {
            "total_discussions": total,
            "total_tokens_used": total_tokens,
            "total_cost_usd": total_cost,
            "confidence_distribution": confidence_dist,
            "hat_distribution": hat_dist,
        }

    async def persona_stats(
        self,
        *,
        user_id: str | None = None,
        team_id: str | None = None,
    ) -> list[dict[str, Any]]:
        stmt = (
            select(
                PanelistOutputDB.persona_id,
                PanelistOutputDB.hat,
                func.count(),
            )
            .join(RoundDB)
            .join(TreeNodeDB)
            .join(DiscussionDB)
            .group_by(PanelistOutputDB.persona_id, PanelistOutputDB.hat)
        )
        if team_id:
            stmt = stmt.where(DiscussionDB.team_id == team_id)
        elif user_id:
            stmt = stmt.where(DiscussionDB.user_id == user_id)
        rows = (await self.session.execute(stmt)).all()
        return [
            {"persona_id": row[0], "hat": row[1], "count": row[2]}
            for row in rows
        ]
