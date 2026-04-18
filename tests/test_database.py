"""Tests for Phase 5: Database models, repository, auth, API routes, migrator."""

from __future__ import annotations

import os
import uuid
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
import yaml
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from hexmind.archive.migrator import ArchiveMigrator
from hexmind.archive.db_models import (
    Base,
    CitationDB,
    DiscussionDB,
    DiscussionTagDB,
    KnowledgeItemDB,
    PanelistOutputDB,
    RoundDB,
    TeamDB,
    TeamMemberDB,
    TreeNodeDB,
    UserDB,
)
from hexmind.archive.repository import (
    AnalyticsRepository,
    DiscussionRepository,
    KnowledgeRepository,
    TeamRepository,
    TreeRepository,
    UserRepository,
)
from hexmind.auth.service import (
    create_access_token,
    decode_access_token,
    hash_password,
    verify_password,
)
from hexmind.events.consumers.db_writer import DBWriter
from hexmind.events.types import (
    BlueHatDecisionPayload,
    ConclusionPayload,
    DiscussionStartedPayload,
    Event,
    EventType,
    PanelistOutputPayload,
)
from hexmind.models.llm import TokenUsage


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
async def engine():
    """In-memory SQLite async engine for testing."""
    eng = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with eng.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield eng
    await eng.dispose()


@pytest.fixture
async def session(engine) -> AsyncSession:
    factory = async_sessionmaker(engine, expire_on_commit=False)
    async with factory() as sess:
        yield sess


@pytest.fixture
async def session_factory(engine):
    return async_sessionmaker(engine, expire_on_commit=False)


@pytest.fixture(autouse=True)
def _set_jwt_secret(monkeypatch):
    """Ensure JWT_SECRET is set for all tests."""
    monkeypatch.setenv("JWT_SECRET", "test-secret-key-for-testing-only-12345678")


# ---------------------------------------------------------------------------
# Auth service tests
# ---------------------------------------------------------------------------


class TestPasswordHashing:
    def test_hash_and_verify(self):
        hashed = hash_password("my-secure-password")
        assert hashed != "my-secure-password"
        assert verify_password("my-secure-password", hashed)

    def test_wrong_password(self):
        hashed = hash_password("correct-password")
        assert not verify_password("wrong-password", hashed)


class TestJWT:
    def test_create_and_decode(self):
        user_id = str(uuid.uuid4())
        token = create_access_token(user_id)
        payload = decode_access_token(token)
        assert payload["sub"] == user_id

    def test_expired_token(self):
        import jwt as pyjwt

        token = create_access_token("user-123", expires_hours=-1)
        with pytest.raises(pyjwt.ExpiredSignatureError):
            decode_access_token(token)


# ---------------------------------------------------------------------------
# User repository tests
# ---------------------------------------------------------------------------


class TestUserRepository:
    async def test_create_user(self, session: AsyncSession):
        repo = UserRepository(session)
        user = await repo.create(
            email="test@example.com",
            display_name="Test User",
            password_hash=hash_password("password"),
        )
        assert user.id
        assert user.email == "test@example.com"
        assert user.settings == {
            "ui_preferences": {
                "ui_locale": "zh",
                "theme_mode": "system",
            },
            "discussion_preferences": {
                "default_discussion_locale": "zh",
                "default_selected_model_id": None,
                "default_analysis_depth": None,
                "default_execution_token_cap": None,
                "default_discussion_max_rounds": None,
                "default_time_budget_seconds": None,
            },
            "feature_flags": {},
        }

    async def test_get_by_email(self, session: AsyncSession):
        repo = UserRepository(session)
        await repo.create(
            email="find@example.com",
            display_name="Find Me",
            password_hash="hash",
        )
        found = await repo.get_by_email("find@example.com")
        assert found is not None
        assert found.display_name == "Find Me"

    async def test_get_by_email_not_found(self, session: AsyncSession):
        repo = UserRepository(session)
        found = await repo.get_by_email("nonexistent@example.com")
        assert found is None

    async def test_create_normalizes_legacy_settings_shape(self, session: AsyncSession):
        repo = UserRepository(session)
        user = await repo.create(
            email="legacy@example.com",
            display_name="Legacy",
            password_hash="hash",
            settings={
                "locale": "en",
                "theme": "dark",
                "token_budget": 75000,
                "selected_model": "gpt",
                "beta_discussion_timeline": True,
            },
        )

        assert user.settings["ui_preferences"] == {
            "ui_locale": "en",
            "theme_mode": "dark",
        }
        assert user.settings["discussion_preferences"] == {
            "default_discussion_locale": "zh",
            "default_selected_model_id": "gpt",
            "default_analysis_depth": None,
            "default_execution_token_cap": 75000,
            "default_discussion_max_rounds": None,
            "default_time_budget_seconds": None,
        }
        assert user.settings["feature_flags"] == {"beta_discussion_timeline": True}


# ---------------------------------------------------------------------------
# Team repository tests
# ---------------------------------------------------------------------------


class TestTeamRepository:
    async def test_create_team(self, session: AsyncSession):
        user_repo = UserRepository(session)
        user = await user_repo.create(
            email="owner@example.com", display_name="Owner", password_hash="h"
        )
        team_repo = TeamRepository(session)
        team = await team_repo.create(name="My Team", owner_id=user.id)
        assert team.name == "My Team"

        # Owner should be auto-added as member
        role = await team_repo.get_member_role(team.id, user.id)
        assert role == "owner"

    async def test_add_and_remove_member(self, session: AsyncSession):
        user_repo = UserRepository(session)
        owner = await user_repo.create(
            email="owner2@example.com", display_name="Owner", password_hash="h"
        )
        member = await user_repo.create(
            email="member@example.com", display_name="Member", password_hash="h"
        )
        team_repo = TeamRepository(session)
        team = await team_repo.create(name="Team X", owner_id=owner.id)

        await team_repo.add_member(team_id=team.id, user_id=member.id, role="member")
        assert await team_repo.get_member_role(team.id, member.id) == "member"

        removed = await team_repo.remove_member(team_id=team.id, user_id=member.id)
        assert removed is True
        assert await team_repo.get_member_role(team.id, member.id) is None

    async def test_cannot_remove_owner(self, session: AsyncSession):
        user_repo = UserRepository(session)
        owner = await user_repo.create(
            email="ownerx@example.com", display_name="Owner", password_hash="h"
        )
        team_repo = TeamRepository(session)
        team = await team_repo.create(name="Team Y", owner_id=owner.id)

        removed = await team_repo.remove_member(team_id=team.id, user_id=owner.id)
        assert removed is False

    async def test_list_for_user(self, session: AsyncSession):
        user_repo = UserRepository(session)
        user = await user_repo.create(
            email="lister@example.com", display_name="Lister", password_hash="h"
        )
        team_repo = TeamRepository(session)
        await team_repo.create(name="Team A", owner_id=user.id)
        await team_repo.create(name="Team B", owner_id=user.id)
        teams = await team_repo.list_for_user(user.id)
        assert len(teams) == 2


# ---------------------------------------------------------------------------
# Discussion repository tests
# ---------------------------------------------------------------------------


class TestDiscussionRepository:
    async def test_create_and_get(self, session: AsyncSession):
        repo = DiscussionRepository(session)
        disc = await repo.create(
            question="Should we use PostgreSQL?",
            config={"max_rounds": 12},
            model_used="gpt-4o",
        )
        assert disc.id
        assert disc.question == "Should we use PostgreSQL?"

        fetched = await repo.get_by_id(disc.id)
        assert fetched is not None
        assert fetched.status == "running"
        assert fetched.config["runtime_config_snapshot"]["max_rounds"] == 12
        assert fetched.config["request_config_snapshot"] == {}
        assert fetched.config["migration_metadata"] == {}

    async def test_update_status(self, session: AsyncSession):
        repo = DiscussionRepository(session)
        disc = await repo.create(question="Test Q", config={})
        await repo.update_status(
            disc.id,
            status="converged",
            verdict={"summary": "Yes"},
            confidence="high",
            total_tokens=5000,
        )
        updated = await repo.get_by_id(disc.id)
        assert updated.status == "converged"
        assert updated.verdict == {"summary": "Yes"}
        assert updated.completed_at is not None

    async def test_search_by_keyword(self, session: AsyncSession):
        repo = DiscussionRepository(session)
        await repo.create(question="Should we migrate to PostgreSQL?", config={})
        await repo.create(question="How to deploy on AWS?", config={})
        results = await repo.search("PostgreSQL")
        assert len(results) == 1
        assert "PostgreSQL" in results[0].question

    async def test_set_tags(self, session: AsyncSession):
        repo = DiscussionRepository(session)
        disc = await repo.create(question="Tag test", config={})
        await repo.set_tags(disc.id, ["architecture", "database"])
        fetched = await repo.get_by_id(disc.id)
        tag_values = [t.tag for t in fetched.tags]
        assert "architecture" in tag_values
        assert "database" in tag_values

    async def test_delete(self, session: AsyncSession):
        repo = DiscussionRepository(session)
        disc = await repo.create(question="To delete", config={})
        deleted = await repo.delete(disc.id)
        assert deleted is True
        assert await repo.get_by_id(disc.id) is None


# ---------------------------------------------------------------------------
# Tree repository tests
# ---------------------------------------------------------------------------


class TestTreeRepository:
    async def test_create_node_and_round(self, session: AsyncSession):
        disc_repo = DiscussionRepository(session)
        disc = await disc_repo.create(question="Tree test", config={})

        tree_repo = TreeRepository(session)
        node = await tree_repo.create_node(
            discussion_id=disc.id, question="Root question"
        )
        assert node.depth == 0

        rnd = await tree_repo.create_round(
            tree_node_id=node.id, round_number=1, hat="white"
        )
        assert rnd.hat == "white"

        output = await tree_repo.create_panelist_output(
            round_id=rnd.id,
            persona_id="backend-engineer",
            hat="white",
            content="Facts here",
            raw_content="Facts here raw",
            items=[{"id": "W1", "content": "Fact 1", "references": []}],
            token_usage={"prompt": 100, "completion": 50},
        )
        assert output.persona_id == "backend-engineer"

    async def test_get_full_tree(self, session: AsyncSession):
        disc_repo = DiscussionRepository(session)
        disc = await disc_repo.create(question="Full tree", config={})

        tree_repo = TreeRepository(session)
        node = await tree_repo.create_node(
            discussion_id=disc.id, question="Root"
        )
        rnd = await tree_repo.create_round(
            tree_node_id=node.id, round_number=1, hat="white"
        )
        await tree_repo.create_panelist_output(
            round_id=rnd.id,
            persona_id="pm",
            hat="white",
            content="c",
            raw_content="r",
            items=[],
            token_usage={},
        )

        tree = await tree_repo.get_full_tree(disc.id)
        assert len(tree) == 1
        assert len(tree[0].rounds) == 1
        assert len(tree[0].rounds[0].outputs) == 1


# ---------------------------------------------------------------------------
# Knowledge repository tests
# ---------------------------------------------------------------------------


class TestKnowledgeRepository:
    async def test_upsert_item(self, session: AsyncSession):
        repo = KnowledgeRepository(session)
        item = await repo.upsert_item(
            source="semantic_scholar",
            external_id="abc123",
            title="Test Paper",
            year=2024,
            authors=["Author A"],
        )
        assert item.title == "Test Paper"

        # Upsert same item updates it
        updated = await repo.upsert_item(
            source="semantic_scholar",
            external_id="abc123",
            title="Updated Title",
        )
        assert updated.id == item.id
        assert updated.title == "Updated Title"


# ---------------------------------------------------------------------------
# Analytics repository tests
# ---------------------------------------------------------------------------


class TestAnalyticsRepository:
    async def test_summary_empty(self, session: AsyncSession):
        repo = AnalyticsRepository(session)
        summary = await repo.summary()
        assert summary["total_discussions"] == 0

    async def test_summary_with_data(self, session: AsyncSession):
        disc_repo = DiscussionRepository(session)
        user_repo = UserRepository(session)
        user = await user_repo.create(
            email="analyst@example.com", display_name="Analyst", password_hash="h"
        )
        d1 = await disc_repo.create(
            question="Q1", config={}, user_id=user.id
        )
        await disc_repo.update_status(
            d1.id, status="converged", confidence="high", total_tokens=1000
        )
        d2 = await disc_repo.create(
            question="Q2", config={}, user_id=user.id
        )
        await disc_repo.update_status(
            d2.id, status="converged", confidence="low", total_tokens=2000
        )

        repo = AnalyticsRepository(session)
        summary = await repo.summary(user_id=user.id)
        assert summary["total_discussions"] == 2
        assert summary["total_tokens_used"] == 3000


# ---------------------------------------------------------------------------
# DBWriter event consumer tests
# ---------------------------------------------------------------------------


class TestDBWriter:
    async def test_full_discussion_lifecycle(self, session_factory):
        writer = DBWriter(session_factory)

        # discussion_started
        await writer.on_event(Event(
            type=EventType.DISCUSSION_STARTED,
            payload=DiscussionStartedPayload(
                question="Should we use microservices?",
                root_node_id="node_abc",
                runtime_config_snapshot={"max_rounds": 12},
                resolved_model_slug="gpt-4o",
            ),
        ))
        assert writer._discussion_id is not None

        # blue_hat_decision
        await writer.on_event(Event(
            type=EventType.BLUE_HAT_DECISION,
            payload=BlueHatDecisionPayload(
                node_id="node_abc",
                round=1,
                hat="white",
                reasoning="Start with facts",
            ),
        ))

        # panelist_output
        await writer.on_event(Event(
            type=EventType.PANELIST_OUTPUT,
            payload=PanelistOutputPayload(
                node_id="node_abc",
                round=1,
                persona_id="backend-engineer",
                hat="white",
                content="Microservices provide scalability",
                raw_content="raw",
                items=[{"id": "W1", "content": "Scalability benefit"}],
                token_usage=TokenUsage(total_tokens=150),
            ),
        ))

        # conclusion
        await writer.on_event(Event(
            type=EventType.CONCLUSION,
            payload=ConclusionPayload(
                summary="Adopt microservices gradually",
                confidence="high",
                token_usage=TokenUsage(total_tokens=5000),
            ),
        ))

        # Verify data was persisted
        async with session_factory() as session:
            disc_repo = DiscussionRepository(session)
            disc = await disc_repo.get_by_id(writer._discussion_id)
            assert disc is not None
            assert disc.status == "converged"
            assert disc.confidence == "high"

            tree_repo = TreeRepository(session)
            nodes = await tree_repo.get_full_tree(disc.id)
            assert len(nodes) == 1
            assert len(nodes[0].rounds) == 1
            assert len(nodes[0].rounds[0].outputs) == 1

    async def test_cancel_persists_partial_verdict(self, session_factory):
        writer = DBWriter(session_factory)

        await writer.on_event(Event(
            type=EventType.DISCUSSION_STARTED,
            data={
                "question": "Should we stop now?",
                "config": {},
                "model": "gpt-4o",
                "root_node_id": "node_cancel",
            },
        ))
        await writer.on_event(Event(
            type=EventType.DISCUSSION_CANCELLED,
            data={
                "summary": "Stop with partial result",
                "confidence": "low",
                "key_facts": ["W1"],
                "key_risks": [],
                "key_values": [],
                "mitigations": [],
                "next_actions": [],
                "blue_hat_ruling": "Cancelled by user",
            },
        ))

        async with session_factory() as session:
            disc_repo = DiscussionRepository(session)
            disc = await disc_repo.get_by_id(writer._discussion_id)
            assert disc is not None
            assert disc.status == "cancelled"
            assert disc.verdict is not None
            assert disc.verdict["summary"] == "Stop with partial result"

    async def test_partial_conclusion_persists_partial_status(self, session_factory):
        writer = DBWriter(session_factory)

        await writer.on_event(Event(
            type=EventType.DISCUSSION_STARTED,
            data={
                "question": "Should we stop at max rounds?",
                "config": {},
                "model": "gpt-4o",
                "root_node_id": "node_partial",
            },
        ))
        await writer.on_event(Event(
            type=EventType.CONCLUSION,
            data={
                "summary": "Partial but useful result",
                "confidence": "medium",
                "key_facts": [],
                "key_risks": [],
                "key_values": [],
                "mitigations": [],
                "next_actions": [],
                "blue_hat_ruling": "Stopped due to limit",
                "partial": True,
            },
        ))

        async with session_factory() as session:
            disc_repo = DiscussionRepository(session)
            disc = await disc_repo.get_by_id(writer._discussion_id)
            assert disc is not None
            assert disc.status == "partial"
            assert disc.verdict is not None
            assert disc.verdict["summary"] == "Partial but useful result"


# ---------------------------------------------------------------------------
# Archive backend tests
# ---------------------------------------------------------------------------


class TestJSONArchive:
    async def test_list_recent_empty(self):
        from hexmind.archive.json_archive import JSONArchive

        archive = JSONArchive("nonexistent_dir_xyz")
        result = await archive.list_recent()
        assert result == []


class TestDBArchive:
    async def test_save_and_get(self, session_factory):
        from hexmind.archive.backend import DiscussionRecord
        from hexmind.archive.db_archive import DBArchive

        archive = DBArchive(session_factory)
        record = DiscussionRecord(
            id="temp",
            question="DB archive test",
            status="running",
            config={"max_rounds": 6},
        )
        disc_id = await archive.save_and_get(record) if False else await archive.save_discussion(record)
        assert disc_id

        fetched = await archive.get_discussion(disc_id)
        assert fetched is not None
        assert fetched.question == "DB archive test"

    async def test_delete(self, session_factory):
        from hexmind.archive.backend import DiscussionRecord
        from hexmind.archive.db_archive import DBArchive

        archive = DBArchive(session_factory)
        record = DiscussionRecord(
            id="temp", question="To delete", status="running", config={}
        )
        disc_id = await archive.save_discussion(record)
        assert await archive.delete(disc_id)
        assert await archive.get_discussion(disc_id) is None


class TestArchiveMigrator:
    async def test_migrator_uses_archive_source_identity_for_idempotency(
        self, session_factory, tmp_path
    ):
        archive_dir = tmp_path / "archive"
        archive_dir.mkdir()

        for dir_name in ("2026-04-15_same-question-a", "2026-04-15_same-question-b"):
            entry_dir = archive_dir / dir_name
            entry_dir.mkdir()
            (entry_dir / "meta.yaml").write_text(
                yaml.safe_dump(
                    {
                        "question": "Should we replatform the backend?",
                        "status": "converged",
                        "confidence": "high",
                        "personas": ["backend-engineer", "cfo"],
                        "verdict": "Proceed carefully",
                        "created_at": "2026-04-15T00:00:00Z",
                    },
                    allow_unicode=True,
                    sort_keys=False,
                ),
                encoding="utf-8",
            )
            (entry_dir / "discussion.md").write_text(
                "# Discussion\n\n## Round 1 - White Hat\nW1: Fact\n",
                encoding="utf-8",
            )

        migrator = ArchiveMigrator(session_factory)
        migrated = await migrator.migrate_all(str(archive_dir))
        migrated_again = await migrator.migrate_all(str(archive_dir))

        assert migrated == 2
        assert migrated_again == 0

        async with session_factory() as session:
            repo = DiscussionRepository(session)
            discussions = await repo.search("Should we replatform the backend?")
            assert len(discussions) == 2
            assert sorted(
                d.config["migration_metadata"]["archive_source_dir"]
                for d in discussions
            ) == [
                "2026-04-15_same-question-a",
                "2026-04-15_same-question-b",
            ]


# ---------------------------------------------------------------------------
# API route tests (with httpx TestClient)
# ---------------------------------------------------------------------------


@pytest.fixture
async def db_app(engine, session_factory, monkeypatch):
    """Create a FastAPI app with an in-memory DB for testing auth routes."""
    from hexmind.archive import database as db_module
    from hexmind.api.app import create_app

    # Patch the database module to use our test engine
    monkeypatch.setattr(db_module, "_engine", engine)
    monkeypatch.setattr(db_module, "_session_factory", session_factory)

    app = create_app()
    return app


@pytest.fixture
async def client(db_app):
    from httpx import ASGITransport, AsyncClient

    transport = ASGITransport(app=db_app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


class TestAuthAPI:
    async def test_register(self, client):
        resp = await client.post("/api/auth/register", json={
            "email": "new@example.com",
            "display_name": "New User",
            "password": "password123",
        })
        assert resp.status_code == 201
        data = resp.json()
        assert "access_token" in data
        assert data["display_name"] == "New User"

    async def test_register_duplicate(self, client):
        await client.post("/api/auth/register", json={
            "email": "dup@example.com",
            "display_name": "Dup",
            "password": "password123",
        })
        resp = await client.post("/api/auth/register", json={
            "email": "dup@example.com",
            "display_name": "Dup2",
            "password": "password456",
        })
        assert resp.status_code == 400  # generic error to prevent email enumeration

    async def test_login(self, client):
        await client.post("/api/auth/register", json={
            "email": "login@example.com",
            "display_name": "Login User",
            "password": "mypassword",
        })
        resp = await client.post("/api/auth/login", json={
            "email": "login@example.com",
            "password": "mypassword",
        })
        assert resp.status_code == 200
        assert "access_token" in resp.json()

    async def test_login_wrong_password(self, client):
        await client.post("/api/auth/register", json={
            "email": "bad@example.com",
            "display_name": "Bad",
            "password": "correct-pw",
        })
        resp = await client.post("/api/auth/login", json={
            "email": "bad@example.com",
            "password": "wrong-pw",
        })
        assert resp.status_code == 401

    async def test_me(self, client):
        reg = await client.post("/api/auth/register", json={
            "email": "me@example.com",
            "display_name": "Me",
            "password": "password123",
        })
        token = reg.json()["access_token"]
        resp = await client.get(
            "/api/auth/me", headers={"Authorization": f"Bearer {token}"}
        )
        assert resp.status_code == 200
        assert resp.json()["email"] == "me@example.com"

    async def test_me_settings_returns_namespaced_structure(self, client):
        reg = await client.post("/api/auth/register", json={
            "email": "settings@example.com",
            "display_name": "Settings User",
            "password": "password123",
        })
        token = reg.json()["access_token"]

        resp = await client.get(
            "/api/auth/me/settings",
            headers={"Authorization": f"Bearer {token}"},
        )

        assert resp.status_code == 200
        assert resp.json() == {
            "ui_preferences": {
                "ui_locale": "zh",
                "theme_mode": "system",
            },
            "discussion_preferences": {
                "default_discussion_locale": "zh",
                "default_selected_model_id": None,
                "default_analysis_depth": None,
                "default_execution_token_cap": None,
                "default_discussion_max_rounds": None,
                "default_time_budget_seconds": None,
            },
            "feature_flags": {},
        }

    async def test_update_me_settings_merges_namespaces(self, client):
        reg = await client.post("/api/auth/register", json={
            "email": "settings-update@example.com",
            "display_name": "Settings Update User",
            "password": "password123",
        })
        token = reg.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        resp = await client.put(
            "/api/auth/me/settings",
            headers=headers,
            json={
                "ui_preferences": {"ui_locale": "en"},
                "discussion_preferences": {
                    "default_selected_model_id": "opus",
                    "default_analysis_depth": "deep",
                    "default_execution_token_cap": 90000,
                },
                "feature_flags": {"beta_discussion_timeline": True},
            },
        )

        assert resp.status_code == 200
        assert resp.json() == {
            "ui_preferences": {
                "ui_locale": "en",
                "theme_mode": "system",
            },
            "discussion_preferences": {
                "default_discussion_locale": "zh",
                "default_selected_model_id": "opus",
                "default_analysis_depth": "deep",
                "default_execution_token_cap": 90000,
                "default_discussion_max_rounds": None,
                "default_time_budget_seconds": None,
            },
            "feature_flags": {
                "beta_discussion_timeline": True,
            },
        }

    async def test_me_no_token(self, client):
        resp = await client.get("/api/auth/me")
        assert resp.status_code == 401


class TestTeamAPI:
    async def _register(self, client, email: str) -> str:
        resp = await client.post("/api/auth/register", json={
            "email": email,
            "display_name": email.split("@")[0],
            "password": "password123",
        })
        return resp.json()["access_token"]

    async def test_create_team(self, client):
        token = await self._register(client, "team-owner@example.com")
        resp = await client.post(
            "/api/teams",
            json={"name": "Alpha Team"},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["name"] == "Alpha Team"
        assert data["role"] == "owner"

    async def test_list_teams(self, client):
        token = await self._register(client, "multi-team@example.com")
        headers = {"Authorization": f"Bearer {token}"}
        await client.post("/api/teams", json={"name": "T1"}, headers=headers)
        await client.post("/api/teams", json={"name": "T2"}, headers=headers)
        resp = await client.get("/api/teams", headers=headers)
        assert resp.status_code == 200
        assert len(resp.json()) >= 2


class TestProtectedDiscussionAPI:
    async def test_create_discussion_allows_anonymous_via_trial_gate(self, client):
        """Anonymous create is allowed by the trial gate (was 401 before BYOK rollout).

        The fixture does not wire DiscussionRegistry, so a successful gate check
        propagates a RuntimeError from downstream wiring. We only assert here
        that the route no longer rejects with 401 — the trial gate replaced the
        hard auth requirement on this endpoint.
        """
        import pytest

        with pytest.raises(RuntimeError, match="DiscussionRegistry not initialized"):
            await client.post(
                "/api/discussions/",
                json={
                    "question": "Should we launch feature X?",
                    "persona_ids": ["backend-engineer", "tech-lead"],
                },
            )

    async def test_discussion_archive_persona_routes_require_auth(self, client):
        assert (await client.get("/api/discussions/nonexistent")).status_code == 401
        assert (await client.post("/api/discussions/nonexistent/cancel")).status_code == 401
        assert (await client.get("/api/archive/")).status_code == 401
        assert (await client.get("/api/personas/")).status_code == 401

    async def test_discussion_routes_enforce_owner_access(self, client, db_app, session_factory):
        from hexmind.api.registry import DiscussionRegistry
        from hexmind.api.routes_discussions import init_discussion_routes
        from hexmind.personas.loader import PersonaLoader

        owner_reg = await client.post("/api/auth/register", json={
            "email": "owner-discussion@example.com",
            "display_name": "Owner",
            "password": "password123",
        })
        other_reg = await client.post("/api/auth/register", json={
            "email": "other-discussion@example.com",
            "display_name": "Other",
            "password": "password123",
        })
        owner_user_id = owner_reg.json()["user_id"]
        owner_headers = {"Authorization": f"Bearer {owner_reg.json()['access_token']}"}
        other_headers = {"Authorization": f"Bearer {other_reg.json()['access_token']}"}

        registry = DiscussionRegistry()
        init_discussion_routes(db_app, registry, PersonaLoader(), session_factory)

        root = SimpleNamespace(rounds=[])
        orch = SimpleNamespace(
            tree=SimpleNamespace(root=root),
            budget=SimpleNamespace(total_tokens=0),
            config=SimpleNamespace(execution_token_cap=5000),
            cancel=AsyncMock(),
            intervene=AsyncMock(),
            get_status_snapshot=lambda: {
                "rounds_completed": 0,
                "token_used": 0,
                "execution_token_cap": 5000,
            },
        )
        registry.register(
            discussion_id="owned-discussion",
            question="Owner only question",
            persona_ids=["backend-engineer", "tech-lead"],
            orchestrator=orch,
            event_bus=SimpleNamespace(get_listeners=lambda: []),
            user_id=owner_user_id,
        )

        owner_resp = await client.get("/api/discussions/owned-discussion", headers=owner_headers)
        assert owner_resp.status_code == 200
        owner_data = owner_resp.json()
        assert owner_data["run_state"] == "running"
        assert owner_data["completion_status"] is None
        assert owner_data["execution_token_cap"] == 5000

        other_resp = await client.get("/api/discussions/owned-discussion", headers=other_headers)
        assert other_resp.status_code == 404

        cancel_resp = await client.post(
            "/api/discussions/owned-discussion/cancel",
            headers=owner_headers,
        )
        assert cancel_resp.status_code == 200
        orch.cancel.assert_awaited_once()

    async def test_stream_route_hides_other_users_discussion(self, client, db_app, session_factory):
        from hexmind.api.registry import DiscussionRegistry
        from hexmind.api.routes_discussions import init_discussion_routes
        from hexmind.personas.loader import PersonaLoader

        owner_reg = await client.post("/api/auth/register", json={
            "email": "owner-stream@example.com",
            "display_name": "OwnerStream",
            "password": "password123",
        })
        other_reg = await client.post("/api/auth/register", json={
            "email": "other-stream@example.com",
            "display_name": "OtherStream",
            "password": "password123",
        })
        owner_user_id = owner_reg.json()["user_id"]
        other_headers = {"Authorization": f"Bearer {other_reg.json()['access_token']}"}

        registry = DiscussionRegistry()
        init_discussion_routes(db_app, registry, PersonaLoader(), session_factory)
        root = SimpleNamespace(rounds=[])
        orch = SimpleNamespace(
            tree=SimpleNamespace(root=root),
            budget=SimpleNamespace(total_tokens=0),
            config=SimpleNamespace(execution_token_cap=5000),
            cancel=AsyncMock(),
            intervene=AsyncMock(),
            get_status_snapshot=lambda: {
                "rounds_completed": 0,
                "token_used": 0,
                "execution_token_cap": 5000,
            },
        )
        registry.register(
            discussion_id="stream-owned",
            question="Secret stream",
            persona_ids=["backend-engineer", "tech-lead"],
            orchestrator=orch,
            event_bus=SimpleNamespace(get_listeners=lambda: []),
            user_id=owner_user_id,
        )

        resp = await client.get("/api/discussions/stream-owned/stream", headers=other_headers)
        assert resp.status_code == 404

    async def test_archive_routes_filter_by_owner(self, client, db_app, tmp_path):
        from hexmind.api.routes_archive_personas import init_archive_routes
        from hexmind.archive.reader import ArchiveReader
        from hexmind.archive.search import ArchiveSearch

        owner_reg = await client.post("/api/auth/register", json={
            "email": "archive-owner@example.com",
            "display_name": "ArchiveOwner",
            "password": "password123",
        })
        other_reg = await client.post("/api/auth/register", json={
            "email": "archive-other@example.com",
            "display_name": "ArchiveOther",
            "password": "password123",
        })
        owner_user_id = owner_reg.json()["user_id"]
        owner_headers = {"Authorization": f"Bearer {owner_reg.json()['access_token']}"}
        other_headers = {"Authorization": f"Bearer {other_reg.json()['access_token']}"}

        archive_dir = tmp_path / "archive"
        entry_dir = archive_dir / "2026-04-13_owner-entry"
        entry_dir.mkdir(parents=True)
        (entry_dir / "meta.yaml").write_text(
            yaml.safe_dump(
                {
                    "question": "Owner archive",
                    "created_at": "2026-04-13T00:00:00+00:00",
                    "status": "completed",
                    "personas": ["backend-engineer", "tech-lead"],
                    "verdict": "Only owner can read",
                    "confidence": "high",
                    "user_id": owner_user_id,
                },
                allow_unicode=True,
                sort_keys=False,
            ),
            encoding="utf-8",
        )
        (entry_dir / "discussion.md").write_text("secret archive", encoding="utf-8")

        init_archive_routes(db_app, ArchiveReader(str(archive_dir)), ArchiveSearch(str(archive_dir)))

        owner_list = await client.get("/api/archive/", headers=owner_headers)
        assert owner_list.status_code == 200
        assert owner_list.json()["total"] == 1

        other_list = await client.get("/api/archive/", headers=other_headers)
        assert other_list.status_code == 200
        assert other_list.json()["total"] == 0

        owner_get = await client.get("/api/archive/2026-04-13_owner-entry", headers=owner_headers)
        assert owner_get.status_code == 200

        other_get = await client.get("/api/archive/2026-04-13_owner-entry", headers=other_headers)
        assert other_get.status_code == 404

    async def test_create_persona_is_disabled_in_multi_user_mode(self, client, db_app):
        from hexmind.api.routes_archive_personas import init_persona_routes
        from hexmind.personas.loader import PersonaLoader

        init_persona_routes(db_app, PersonaLoader())

        reg = await client.post("/api/auth/register", json={
            "email": "persona-writer@example.com",
            "display_name": "PersonaWriter",
            "password": "password123",
        })
        headers = {"Authorization": f"Bearer {reg.json()['access_token']}"}

        resp = await client.post(
            "/api/personas/",
            json={
                "id": "custom-safe-persona",
                "name": "Custom Safe Persona",
                "domain": "tech",
                "description": "Should be blocked in multi-user mode",
                "system_prompt_suffix": "",
            },
            headers=headers,
        )
        assert resp.status_code == 403
