"""Integration tests for the HexMind API layer."""

from __future__ import annotations

import asyncio
import json

import pytest
from fastapi.testclient import TestClient

from hexmind.api.app import create_app
from hexmind.api.registry import DiscussionRegistry
from hexmind.api.sse import SSEStreamer
from hexmind.events.bus import EventBus
from hexmind.events.types import Event, EventType


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

    event = Event(type=EventType.ROUND_STARTED, data={"round": 1, "hat": "white"})
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

    event = Event(type=EventType.ROUND_STARTED, data={"round": 1, "hat": "white"})
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
    assert registry.get("test-1") is entry

    registry.mark_completed("test-1", "converged")
    assert entry.status == "converged"

    assert len(registry.list_all()) == 1

    registry.remove("test-1")
    assert registry.get("test-1") is None
