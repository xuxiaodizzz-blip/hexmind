"""SQLAlchemy ORM models for Phase 5 database archive."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import (
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB as PG_JSONB
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
from sqlalchemy.types import JSON


def _pg_jsonb_with_fallback():
    """Use JSONB on PostgreSQL, plain JSON elsewhere (SQLite tests)."""
    return JSON().with_variant(PG_JSONB(), "postgresql")


JSONB = _pg_jsonb_with_fallback


def _utcnow():
    return datetime.now(timezone.utc)


class Base(DeclarativeBase):
    pass


class UserDB(Base):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    display_name: Mapped[str] = mapped_column(String(100), nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    # Clerk integration: when auth provider is Clerk, users are JIT-created with
    # clerk_user_id set and a placeholder password_hash ("clerk:<sub>"). Local
    # email/password users have clerk_user_id=NULL.
    clerk_user_id: Mapped[str | None] = mapped_column(
        String(64), unique=True, nullable=True, index=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow
    )
    last_login_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    settings: Mapped[dict] = mapped_column(JSONB(), default=dict)

    discussions: Mapped[list[DiscussionDB]] = relationship(back_populates="user")
    owned_teams: Mapped[list[TeamDB]] = relationship(back_populates="owner")


class TeamDB(Base):
    __tablename__ = "teams"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    owner_id: Mapped[str] = mapped_column(ForeignKey("users.id"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow
    )

    owner: Mapped[UserDB] = relationship(back_populates="owned_teams")
    members: Mapped[list[TeamMemberDB]] = relationship(
        back_populates="team", cascade="all, delete-orphan"
    )
    discussions: Mapped[list[DiscussionDB]] = relationship(back_populates="team")


class TeamMemberDB(Base):
    __tablename__ = "team_members"

    team_id: Mapped[str] = mapped_column(
        ForeignKey("teams.id", ondelete="CASCADE"), primary_key=True
    )
    user_id: Mapped[str] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
    )
    role: Mapped[str] = mapped_column(String(20), default="member")
    joined_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow
    )

    team: Mapped[TeamDB] = relationship(back_populates="members")
    user: Mapped[UserDB] = relationship()


class DiscussionDB(Base):
    __tablename__ = "discussions"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    user_id: Mapped[str | None] = mapped_column(
        ForeignKey("users.id"), nullable=True
    )
    team_id: Mapped[str | None] = mapped_column(
        ForeignKey("teams.id"), nullable=True
    )
    question: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="running")
    config: Mapped[dict] = mapped_column(JSONB(), nullable=False, default=dict)
    verdict: Mapped[dict | None] = mapped_column(JSONB(), nullable=True)
    confidence: Mapped[str | None] = mapped_column(String(10), nullable=True)
    total_tokens: Mapped[int] = mapped_column(Integer, default=0)
    total_cost_usd: Mapped[float] = mapped_column(Float, default=0.0)
    model_used: Mapped[str | None] = mapped_column(String(50), nullable=True)
    discussion_locale: Mapped[str] = mapped_column("locale", String(5), default="zh")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow
    )
    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    duration_seconds: Mapped[float | None] = mapped_column(Float, nullable=True)

    user: Mapped[UserDB | None] = relationship(back_populates="discussions")
    team: Mapped[TeamDB | None] = relationship(back_populates="discussions")
    tags: Mapped[list[DiscussionTagDB]] = relationship(
        back_populates="discussion", cascade="all, delete-orphan"
    )
    tree_nodes: Mapped[list[TreeNodeDB]] = relationship(
        back_populates="discussion", cascade="all, delete-orphan"
    )
    interventions: Mapped[list[InterventionDB]] = relationship(
        back_populates="discussion", cascade="all, delete-orphan"
    )


class DiscussionTagDB(Base):
    __tablename__ = "discussion_tags"

    discussion_id: Mapped[str] = mapped_column(
        ForeignKey("discussions.id", ondelete="CASCADE"), primary_key=True
    )
    tag: Mapped[str] = mapped_column(String(50), primary_key=True)

    discussion: Mapped[DiscussionDB] = relationship(back_populates="tags")


class TreeNodeDB(Base):
    __tablename__ = "tree_nodes"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    discussion_id: Mapped[str] = mapped_column(
        ForeignKey("discussions.id", ondelete="CASCADE"), nullable=False
    )
    parent_id: Mapped[str | None] = mapped_column(
        ForeignKey("tree_nodes.id"), nullable=True
    )
    question: Mapped[str] = mapped_column(Text, nullable=False)
    depth: Mapped[int] = mapped_column(Integer, default=0)
    status: Mapped[str] = mapped_column(String(20), default="active")
    compressed_context: Mapped[str | None] = mapped_column(Text, nullable=True)
    verdict: Mapped[dict | None] = mapped_column(JSONB(), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow
    )

    discussion: Mapped[DiscussionDB] = relationship(back_populates="tree_nodes")
    children: Mapped[list[TreeNodeDB]] = relationship(
        back_populates="parent",
    )
    parent: Mapped[TreeNodeDB | None] = relationship(
        back_populates="children", remote_side="TreeNodeDB.id"
    )
    rounds: Mapped[list[RoundDB]] = relationship(
        back_populates="tree_node", cascade="all, delete-orphan"
    )


class RoundDB(Base):
    __tablename__ = "rounds"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    tree_node_id: Mapped[str] = mapped_column(
        ForeignKey("tree_nodes.id", ondelete="CASCADE"), nullable=False
    )
    round_number: Mapped[int] = mapped_column(Integer, nullable=False)
    hat: Mapped[str] = mapped_column(String(10), nullable=False)
    blue_hat_reasoning: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow
    )

    tree_node: Mapped[TreeNodeDB] = relationship(back_populates="rounds")
    outputs: Mapped[list[PanelistOutputDB]] = relationship(
        back_populates="round", cascade="all, delete-orphan"
    )


class PanelistOutputDB(Base):
    __tablename__ = "panelist_outputs"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    round_id: Mapped[str] = mapped_column(
        ForeignKey("rounds.id", ondelete="CASCADE"), nullable=False
    )
    persona_id: Mapped[str] = mapped_column(String(50), nullable=False)
    hat: Mapped[str] = mapped_column(String(10), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    raw_content: Mapped[str] = mapped_column(Text, nullable=False)
    items: Mapped[dict] = mapped_column(JSONB(), nullable=False)
    token_usage: Mapped[dict] = mapped_column(JSONB(), nullable=False)
    validation_passed: Mapped[bool] = mapped_column(Boolean, default=True)
    validation_violations: Mapped[list[str]] = mapped_column(JSONB(), default=list)
    retry_count: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow
    )

    round: Mapped[RoundDB] = relationship(back_populates="outputs")
    citations: Mapped[list[CitationDB]] = relationship(
        back_populates="panelist_output", cascade="all, delete-orphan"
    )


class InterventionDB(Base):
    __tablename__ = "interventions"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    discussion_id: Mapped[str] = mapped_column(
        ForeignKey("discussions.id", ondelete="CASCADE"), nullable=False
    )
    user_id: Mapped[str | None] = mapped_column(
        ForeignKey("users.id"), nullable=True
    )
    type: Mapped[str] = mapped_column(String(20), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow
    )

    discussion: Mapped[DiscussionDB] = relationship(back_populates="interventions")


class KnowledgeItemDB(Base):
    __tablename__ = "knowledge_items"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    source: Mapped[str] = mapped_column(String(30), nullable=False)
    external_id: Mapped[str] = mapped_column(String(255), nullable=False)
    title: Mapped[str] = mapped_column(Text, nullable=False)
    snippet: Mapped[str | None] = mapped_column(Text, nullable=True)
    url: Mapped[str | None] = mapped_column(Text, nullable=True)
    year: Mapped[int | None] = mapped_column(Integer, nullable=True)
    authors: Mapped[list[str]] = mapped_column(JSONB(), default=list)
    citation_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    metadata_: Mapped[dict] = mapped_column("metadata", JSONB(), default=dict)

    __table_args__ = (
        UniqueConstraint("source", "external_id", name="uq_knowledge_source_extid"),
    )


class CitationDB(Base):
    __tablename__ = "citations"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    panelist_output_id: Mapped[str] = mapped_column(
        ForeignKey("panelist_outputs.id", ondelete="CASCADE"), nullable=False
    )
    knowledge_item_id: Mapped[str] = mapped_column(
        ForeignKey("knowledge_items.id"), nullable=False
    )
    citation_number: Mapped[int] = mapped_column(Integer, nullable=False)

    panelist_output: Mapped[PanelistOutputDB] = relationship(back_populates="citations")
    knowledge_item: Mapped[KnowledgeItemDB] = relationship()
