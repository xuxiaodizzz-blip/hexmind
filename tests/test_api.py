"""Integration tests for the HexMind API layer."""

from __future__ import annotations

import asyncio
import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from hexmind.api.app import create_app
from hexmind.api.registry import DiscussionRegistry
from hexmind.api.sse import SSEStreamer
from hexmind.events.bus import EventBus
from hexmind.events.types import Event, EventType, RoundStartedPayload
from hexmind.llm.requesty_transport import RequestyTransport
from hexmind.models.llm import LLMResponse, TokenUsage


# ── Fixtures ───────────────────────────────────────────────


@pytest.fixture
def app():
    """Create a test FastAPI app with lifespan."""
    app = create_app()
    return app


@pytest.fixture
def client(app):
    """Synchronous test client with lifespan context."""
    with TestClient(app, raise_server_exceptions=False) as c:
        yield c


# ── Health ─────────────────────────────────────────────────


def test_health(client):
    resp = client.get("/api/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ok"
    assert "database" in data


def test_frontend_bundle_served_from_configured_dist(monkeypatch, tmp_path: Path):
    dist_dir = tmp_path / "web-dist"
    assets_dir = dist_dir / "assets"
    assets_dir.mkdir(parents=True)
    (dist_dir / "index.html").write_text("<html><body>HexMind Local</body></html>", encoding="utf-8")
    (assets_dir / "app.js").write_text("console.log('hexmind');", encoding="utf-8")

    monkeypatch.setenv("HEXMIND_WEB_DIST_DIR", str(dist_dir))

    with TestClient(create_app(), raise_server_exceptions=False) as local_client:
        index = local_client.get("/")
        nested = local_client.get("/app/settings")
        asset = local_client.get("/assets/app.js")

    assert index.status_code == 200
    assert "HexMind Local" in index.text
    assert nested.status_code == 200
    assert "HexMind Local" in nested.text
    assert asset.status_code == 200
    assert "console.log" in asset.text


def test_get_settings_uses_backend_env(monkeypatch):
    monkeypatch.setenv(
        "HEXMIND_MODEL_MAP",
        "opus=anthropic/claude-opus-4-6,gpt=openai/gpt-5.4,sonnet=anthropic/claude-sonnet-4-6",
    )
    monkeypatch.setenv("HEXMIND_DEFAULT_MODEL_ALIAS", "opus")
    monkeypatch.setenv("HEXMIND_TOKEN_BUDGET", "75000")
    monkeypatch.setenv("HEXMIND_MAX_ROUNDS", "9")
    monkeypatch.setenv("HEXMIND_TIME_BUDGET", "900")
    monkeypatch.setenv("HEXMIND_DISCUSSION_LOCALE", "en")

    app = create_app()
    with TestClient(app, raise_server_exceptions=False) as client:
        resp = client.get("/api/settings/")

    assert resp.status_code == 200
    data = resp.json()
    assert data["default_model_id"] == "opus"
    assert [model["id"] for model in data["models"]] == ["opus", "gpt", "sonnet"]
    assert data["models"][0]["label"] == "OPUS4.6"
    assert data["models"][1]["label"] == "GPT5.4"
    assert data["models"][2]["label"] == "SONNET4.6"
    assert data["models"][0]["capabilities"]["reasoning"] is True
    assert data["default_analysis_depth"] == "standard"
    assert [depth["id"] for depth in data["analysis_depths"]] == ["quick", "standard", "deep"]
    assert data["default_execution_token_cap"] == 52500
    assert data["default_discussion_max_rounds"] == 7
    assert data["default_time_budget_seconds"] == 675
    assert data["default_discussion_locale"] == "en"


def test_app_startup_fails_fast_on_invalid_model_catalog(monkeypatch):
    monkeypatch.setenv("HEXMIND_MODEL_MAP", "opus=anthropic/claude-opus-4-6")
    monkeypatch.setenv("HEXMIND_DEFAULT_MODEL_ALIAS", "gpt")

    with pytest.raises(ValueError, match="HEXMIND_DEFAULT_MODEL_ALIAS"):
        with TestClient(create_app(), raise_server_exceptions=False):
            pass


def test_billing_plans_expose_bilingual_copy(client):
    resp = client.get("/api/billing/plans")
    assert resp.status_code == 200

    plans = {plan["id"]: plan for plan in resp.json()}
    assert plans["free"]["name"] == "Free"
    assert plans["free"]["name_zh"] == "免费版"
    assert plans["free"]["features"][0]["text_zh"] == "每月 5 次讨论"
    assert plans["pro"]["description_zh"] == "完整使用 GPT-5.4，充裕积分，满足专业决策需求。"


# ── Personas ───────────────────────────────────────────────


def test_list_personas(client):
    resp = client.get("/api/personas/")
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)
    assert len(data) > 0
    # Each item should have required fields
    for p in data:
        assert "id" in p
        assert "name" in p
        assert "domain" in p


def test_list_personas_filter_domain(client):
    resp = client.get("/api/personas/?domain=tech")
    assert resp.status_code == 200
    data = resp.json()
    assert all(p["domain"] == "tech" for p in data)


def test_get_persona_detail(client):
    # First get the list to find a valid ID
    resp = client.get("/api/personas/")
    personas = resp.json()
    assert len(personas) > 0

    pid = personas[0]["id"]
    resp = client.get(f"/api/personas/{pid}")
    assert resp.status_code == 200
    detail = resp.json()
    assert detail["id"] == pid
    assert "prompt" in detail


def test_get_persona_not_found(client):
    resp = client.get("/api/personas/nonexistent-persona-xyz")
    assert resp.status_code == 404


def test_list_prompts(client):
    resp = client.get("/api/prompts/")
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)
    assert len(data) > 0
    for item in data:
        assert "id" in item
        assert "position" in item
        assert "status" in item
        assert "hat_context" in item
        assert "applicable_hats" in item
        assert "hat" in item


def test_get_prompt_detail(client):
    resp = client.get("/api/prompts/")
    prompts = resp.json()
    assert len(prompts) > 0

    pid = prompts[0]["id"]
    resp = client.get(f"/api/prompts/{pid}")
    assert resp.status_code == 200
    detail = resp.json()
    assert detail["id"] == pid
    assert "prompt" in detail
    assert "prompt_mode" in detail
    assert "hat" in detail


def test_list_prompts_filter_hat(client):
    resp = client.get("/api/prompts/?hat=white")
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)
    assert any("white" in item["applicable_hats"] for item in data)


# ── Archive ────────────────────────────────────────────────


def test_list_archives_empty(client):
    """Archive list returns empty when no discussions have been archived."""
    resp = client.get("/api/archive/")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] >= 0
    assert isinstance(data["items"], list)


def test_get_archive_not_found(client):
    resp = client.get("/api/archive/nonexistent-archive-xyz")
    assert resp.status_code == 404


# ── Discussion ─────────────────────────────────────────────


def test_create_discussion_bad_persona(client):
    """Creating a discussion with unknown persona IDs returns 422."""
    resp = client.post(
        "/api/discussions/",
        json={
            "question": "Should we launch feature X?",
            "persona_ids": ["fake-persona-1", "fake-persona-2"],
        },
    )
    assert resp.status_code == 422


def test_create_discussion_accepts_user_selected_model(monkeypatch):
    monkeypatch.setenv(
        "HEXMIND_MODEL_MAP",
        "opus=anthropic/claude-opus-4-6,gpt=openai/gpt-5.4,sonnet=anthropic/claude-sonnet-4-6",
    )
    monkeypatch.setenv("HEXMIND_DEFAULT_MODEL_ALIAS", "opus")

    app = create_app()
    with TestClient(app, raise_server_exceptions=False) as client:
        resp = client.post(
            "/api/discussions/",
            json={
                "question": "Should we launch feature X?",
                "persona_ids": ["backend-engineer", "cfo"],
                "config": {"selected_model": "gpt"},
            },
        )

    assert resp.status_code == 200
    assert resp.json()["status"] == "running"


def test_create_discussion_accepts_legacy_model_alias_field(monkeypatch):
    monkeypatch.setenv(
        "HEXMIND_MODEL_MAP",
        "opus=anthropic/claude-opus-4-6,gpt=openai/gpt-5.4,sonnet=anthropic/claude-sonnet-4-6",
    )
    monkeypatch.setenv("HEXMIND_DEFAULT_MODEL_ALIAS", "opus")

    app = create_app()
    with TestClient(app, raise_server_exceptions=False) as client:
        resp = client.post(
            "/api/discussions/",
            json={
                "question": "Should we launch feature X?",
                "persona_ids": ["backend-engineer", "cfo"],
                "config": {"model": "opus"},
            },
        )

    assert resp.status_code == 200
    assert resp.json()["status"] == "running"


def test_create_discussion_rejects_unknown_model_alias(monkeypatch):
    monkeypatch.setenv("HEXMIND_MODEL_MAP", "opus=anthropic/claude-opus-4-6")
    monkeypatch.setenv("HEXMIND_DEFAULT_MODEL_ALIAS", "opus")

    app = create_app()
    with TestClient(app, raise_server_exceptions=False) as client:
        resp = client.post(
            "/api/discussions/",
            json={
                "question": "Should we launch feature X?",
                "persona_ids": ["backend-engineer", "cfo"],
                "config": {"selected_model": "unknown"},
            },
        )

    assert resp.status_code == 422
    assert "Unknown selected_model" in resp.json()["detail"]


def test_create_discussion_accepts_discussion_locale_and_legacy_alias(monkeypatch):
    monkeypatch.setenv(
        "HEXMIND_MODEL_MAP",
        "opus=anthropic/claude-opus-4-6,gpt=openai/gpt-5.4",
    )
    monkeypatch.setenv("HEXMIND_DEFAULT_MODEL_ALIAS", "opus")

    app = create_app()
    with TestClient(app, raise_server_exceptions=False) as client:
        resp = client.post(
            "/api/discussions/",
            json={
                "question": "Should we launch feature X?",
                "persona_ids": ["backend-engineer", "cfo"],
                "config": {"discussion_locale": "en"},
            },
        )
        legacy_resp = client.post(
            "/api/discussions/",
            json={
                "question": "Should we launch feature Y?",
                "persona_ids": ["backend-engineer", "cfo"],
                "config": {"locale": "en"},
            },
        )

    assert resp.status_code == 200
    assert legacy_resp.status_code == 200


def test_create_discussion_carries_round_and_time_overrides(monkeypatch):
    import hexmind.api.routes_discussions as discussion_routes

    monkeypatch.setenv(
        "HEXMIND_MODEL_MAP",
        "opus=anthropic/claude-opus-4-6,gpt=openai/gpt-5.4",
    )
    monkeypatch.setenv("HEXMIND_DEFAULT_MODEL_ALIAS", "opus")
    monkeypatch.setenv("HEXMIND_TIME_BUDGET", "900")

    captured: dict[str, object] = {}

    class FakeOrchestrator:
        def __init__(
            self,
            llm,
            personas,
            config,
            bus,
            knowledge_hub=None,
            user_id=None,
            team_id=None,
            request_config_snapshot=None,
        ) -> None:
            captured["config"] = config
            captured["request_config_snapshot"] = request_config_snapshot
            self.last_run_status = None
            self.last_terminal_reason = None

        async def run(self, question: str) -> None:
            return None

        def get_billable_usage(self) -> TokenUsage:
            return TokenUsage()

        def has_partial_verdict(self) -> bool:
            return False

    monkeypatch.setattr(discussion_routes, "Orchestrator", FakeOrchestrator)

    app = create_app()
    with TestClient(app, raise_server_exceptions=False) as client:
        resp = client.post(
            "/api/discussions/",
            json={
                "question": "Should we launch feature X?",
                "persona_ids": ["backend-engineer", "cfo"],
                "config": {
                    "selected_model": "gpt",
                    "discussion_max_rounds": 7,
                    "time_budget_seconds": 900,
                },
            },
        )

    assert resp.status_code == 200
    config = captured["config"]
    request_snapshot = captured["request_config_snapshot"]
    assert getattr(config, "discussion_max_rounds") == 7
    assert getattr(config, "time_budget_seconds") == 900
    assert request_snapshot["discussion_max_rounds"] == 7
    assert request_snapshot["time_budget_seconds"] == 900


def test_chat_route_resolves_selected_model_alias(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "shared-key")
    monkeypatch.setenv("OPENAI_API_BASE", "https://router.example/v1")
    monkeypatch.setenv(
        "HEXMIND_MODEL_MAP",
        "opus=anthropic/claude-opus-4-6,gpt=openai/gpt-5.4,sonnet=anthropic/claude-sonnet-4-6",
    )
    monkeypatch.setenv("HEXMIND_DEFAULT_MODEL_ALIAS", "opus")

    async def fake_complete(self, *, model, messages, temperature=None, max_tokens=None, response_format=None):
        assert model == "anthropic/claude-opus-4-6"
        assert messages == [{"role": "user", "content": "Hello"}]
        return LLMResponse(
            content="Hi there",
            usage=TokenUsage(total_tokens=5),
            model=model,
            finish_reason="stop",
        )

    monkeypatch.setattr(RequestyTransport, "complete", fake_complete)

    app = create_app()
    with TestClient(app, raise_server_exceptions=False) as client:
        resp = client.post(
            "/api/chat/",
            json={
                "selected_model": "opus",
                "messages": [{"role": "user", "content": "Hello"}],
            },
        )

    assert resp.status_code == 200
    data = resp.json()
    assert data["selected_model"] == "opus"
    assert data["resolved_model"] == "anthropic/claude-opus-4-6"
    assert data["content"] == "Hi there"


def test_chat_route_uses_default_model_alias_when_missing(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "shared-key")
    monkeypatch.setenv("OPENAI_API_BASE", "https://router.example/v1")
    monkeypatch.setenv("HEXMIND_MODEL_MAP", "opus=anthropic/claude-opus-4-6")
    monkeypatch.setenv("HEXMIND_DEFAULT_MODEL_ALIAS", "opus")

    async def fake_complete(self, *, model, messages, temperature=None, max_tokens=None, response_format=None):
        assert model == "anthropic/claude-opus-4-6"
        return LLMResponse(
            content="Default model reply",
            usage=TokenUsage(total_tokens=3),
            model=model,
            finish_reason="stop",
        )

    monkeypatch.setattr(RequestyTransport, "complete", fake_complete)

    app = create_app()
    with TestClient(app, raise_server_exceptions=False) as client:
        resp = client.post(
            "/api/chat/",
            json={"messages": [{"role": "user", "content": "Hello"}]},
        )

    assert resp.status_code == 200
    assert resp.json()["selected_model"] == "opus"


def test_chat_route_rejects_unknown_model_alias(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "shared-key")
    monkeypatch.setenv("OPENAI_API_BASE", "https://router.example/v1")
    monkeypatch.setenv("HEXMIND_MODEL_MAP", "opus=anthropic/claude-opus-4-6")
    monkeypatch.setenv("HEXMIND_DEFAULT_MODEL_ALIAS", "opus")

    app = create_app()
    with TestClient(app, raise_server_exceptions=False) as client:
        resp = client.post(
            "/api/chat/",
            json={
                "selected_model": "gpt",
                "messages": [{"role": "user", "content": "Hello"}],
            },
        )

    assert resp.status_code == 422
    assert "Unknown selected_model" in resp.json()["detail"]


def test_chat_route_streams_normalized_events(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "shared-key")
    monkeypatch.setenv("OPENAI_API_BASE", "https://router.example/v1")
    monkeypatch.setenv(
        "HEXMIND_MODEL_MAP",
        "opus=anthropic/claude-opus-4-6,gpt=openai/gpt-5.4,sonnet=anthropic/claude-sonnet-4-6",
    )
    monkeypatch.setenv("HEXMIND_DEFAULT_MODEL_ALIAS", "opus")

    async def fake_stream_completion(self, *, model, messages, temperature=None, max_tokens=None, response_format=None):
        assert model == "openai/gpt-5.4"
        yield {"event": "delta", "data": {"content": "Hi"}}
        yield {"event": "done", "data": {"model": model, "finish_reason": "stop"}}

    monkeypatch.setattr(RequestyTransport, "stream_completion", fake_stream_completion)

    app = create_app()
    with TestClient(app, raise_server_exceptions=False) as client:
        with client.stream(
            "POST",
            "/api/chat/",
            json={
                "selected_model": "gpt",
                "stream": True,
                "messages": [{"role": "user", "content": "Hello"}],
            },
        ) as resp:
            body = "".join(resp.iter_text())

    assert "event: delta" in body
    assert "event: done" in body
    assert '"selected_model": "gpt"' in body
    assert '"resolved_model": "openai/gpt-5.4"' in body


def test_get_discussion_not_found(client):
    resp = client.get("/api/discussions/nonexistent")
    assert resp.status_code == 404


def test_cancel_discussion_not_found(client):
    resp = client.post("/api/discussions/nonexistent/cancel")
    assert resp.status_code == 404


# ── SSEStreamer unit tests ─────────────────────────────────


@pytest.mark.asyncio
async def test_sse_streamer_basic_flow():
    """SSEStreamer fans out events to all listeners."""
    streamer = SSEStreamer()

    q1 = streamer.create_listener()
    q2 = streamer.create_listener()

    event = Event(
        type=EventType.ROUND_STARTED,
        payload=RoundStartedPayload(round=1, hat="white"),
    )
    await streamer.on_event(event)

    msg1 = q1.get_nowait()
    msg2 = q2.get_nowait()
    assert msg1["event"] == "round_started"
    assert msg2["event"] == "round_started"
    assert json.loads(msg1["data"])["round"] == 1


@pytest.mark.asyncio
async def test_sse_streamer_replay():
    """New listener receives replayed events."""
    streamer = SSEStreamer()

    event = Event(
        type=EventType.ROUND_STARTED,
        payload=RoundStartedPayload(round=1, hat="white"),
    )
    await streamer.on_event(event)

    # Late joiner should get the replay
    q = streamer.create_listener()
    msg = q.get_nowait()
    assert msg["event"] == "round_started"


@pytest.mark.asyncio
async def test_sse_streamer_terminal_signals_done():
    """Terminal event causes all listeners to receive None sentinel."""
    streamer = SSEStreamer()
    q = streamer.create_listener()

    event = Event(type=EventType.CONCLUSION, data={"summary": "done"})
    await streamer.on_event(event)

    # Should get the event then the None sentinel
    msg = q.get_nowait()
    assert msg["event"] == "conclusion"
    sentinel = q.get_nowait()
    assert sentinel is None
    assert streamer.finished


@pytest.mark.asyncio
async def test_sse_streamer_replay_with_last_event_id():
    """Replay only events after last_event_id."""
    streamer = SSEStreamer()

    await streamer.on_event(Event(type=EventType.ROUND_STARTED, data={"round": 1, "hat": "white"}))
    await streamer.on_event(Event(type=EventType.PANELIST_OUTPUT, data={"persona": "a", "hat": "white"}))
    await streamer.on_event(Event(type=EventType.ROUND_STARTED, data={"round": 2, "hat": "black"}))

    # Reconnect after event 1 — should only get events 2 and 3
    q = streamer.create_listener(last_event_id=1)
    msgs = []
    while not q.empty():
        msgs.append(q.get_nowait())
    assert len(msgs) == 2
    assert msgs[0]["id"] == 2
    assert msgs[1]["id"] == 3


# ── Registry unit tests ───────────────────────────────────


def test_registry_lifecycle():
    """Register, get, mark completed, list."""
    from unittest.mock import MagicMock

    registry = DiscussionRegistry()
    orch = MagicMock()
    bus = MagicMock()

    entry = registry.register(
        discussion_id="test-1",
        question="Test?",
        persona_ids=["a", "b"],
        orchestrator=orch,
        event_bus=bus,
    )
    assert entry.status == "running"
    assert entry.run_state == "running"
    assert entry.completion_status is None
    assert registry.get("test-1") is entry

    registry.mark_completed("test-1", "converged", termination_reason="natural_convergence")
    assert entry.status == "converged"
    assert entry.run_state == "completed"
    assert entry.completion_status == "converged"
    assert entry.termination_reason == "natural_convergence"

    assert len(registry.list_all()) == 1

    registry.remove("test-1")
    assert registry.get("test-1") is None
