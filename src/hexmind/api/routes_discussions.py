"""API routes — discussion lifecycle (create, stream, intervene, cancel)."""

from __future__ import annotations

import asyncio
import logging
from uuid import uuid4

from fastapi import APIRouter, Depends, FastAPI, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from sse_starlette.sse import EventSourceResponse

from hexmind.api.registry import DiscussionRegistry
from hexmind.api.schemas import (
    CreateDiscussionRequest,
    CreateDiscussionResponse,
    DiscussionStatusResponse,
    InterventionRequest,
)
from hexmind.api.sse import SSEStreamer
from hexmind.auth.dependencies import require_user_if_db_enabled
from hexmind.engine.orchestrator import Orchestrator
from hexmind.events.bus import EventBus
from hexmind.events.consumers.archive_writer import ArchiveWriter
from hexmind.events.consumers.db_writer import DBWriter
from hexmind.events.types import EventType
from hexmind.llm.litellm_wrapper import LiteLLMWrapper
from hexmind.models.config import DiscussionConfig
from hexmind.models.tree import NodeStatus
from hexmind.personas.loader import PersonaLoader

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/discussions", tags=["discussions"])


def init_discussion_routes(
    app: FastAPI,
    registry: DiscussionRegistry,
    persona_loader: PersonaLoader,
    db_session_factory: async_sessionmaker[AsyncSession] | None = None,
) -> None:
    """Wire shared dependencies — called once at app startup."""
    app.state.registry = registry
    app.state.persona_loader = persona_loader
    app.state.db_session_factory = db_session_factory


def _get_registry(request: Request) -> DiscussionRegistry:
    registry = getattr(request.app.state, "registry", None)
    if registry is None:
        raise RuntimeError("DiscussionRegistry not initialized")
    return registry


def _get_loader(request: Request) -> PersonaLoader:
    loader = getattr(request.app.state, "persona_loader", None)
    if loader is None:
        raise RuntimeError("PersonaLoader not initialized")
    return loader


def _get_db_session_factory(
    request: Request,
) -> async_sessionmaker[AsyncSession] | None:
    return getattr(request.app.state, "db_session_factory", None)


# ── Create discussion ──────────────────────────────────────


@router.post("/", response_model=CreateDiscussionResponse)
async def create_discussion(
    request: Request,
    body: CreateDiscussionRequest,
    user=Depends(require_user_if_db_enabled),
):
    """Create a new discussion. Runs asynchronously in the background."""
    registry = _get_registry(request)
    loader = _get_loader(request)

    # Resolve personas
    personas = []
    for pid in body.persona_ids:
        try:
            personas.append(loader.load(pid))
        except FileNotFoundError:
            raise HTTPException(422, f"Unknown persona: {pid}")

    # Build config
    override = body.config or {}
    config_kwargs: dict = {}
    if isinstance(override, dict):
        config_kwargs = override
    else:
        config_kwargs = override.model_dump(exclude_none=True)

    config = DiscussionConfig(
        default_model=config_kwargs.get("model", "gpt-4o"),
        token_budget=config_kwargs.get("token_budget", 50_000),
        locale=config_kwargs.get("locale", "zh"),
    )

    # Create engine components
    llm = LiteLLMWrapper(model=config.default_model)
    bus = EventBus()

    # SSE streamer — events will be fanned out to SSE clients
    streamer = SSEStreamer()
    bus.subscribe(streamer)

    # Archive writer
    writer = ArchiveWriter(config.archive_dir)
    bus.subscribe(writer)

    db_session_factory = _get_db_session_factory(request)
    if db_session_factory is not None:
        bus.subscribe(DBWriter(db_session_factory))

    # Budget tracker is created inside Orchestrator

    orch = Orchestrator(
        llm,
        personas,
        config,
        bus,
        user_id=getattr(user, "id", None),
    )

    discussion_id = uuid4().hex[:12]
    entry = registry.register(
        discussion_id=discussion_id,
        question=body.question,
        persona_ids=body.persona_ids,
        orchestrator=orch,
        event_bus=bus,
        user_id=getattr(user, "id", None),
    )

    # Run discussion in background
    async def _run_and_finalize():
        try:
            await orch.run(body.question)
            if orch.last_run_status == NodeStatus.CANCELLED:
                registry.mark_completed(discussion_id, "cancelled")
            elif orch.has_partial_verdict():
                registry.mark_completed(discussion_id, "partial")
            else:
                registry.mark_completed(discussion_id, "converged")
        except asyncio.CancelledError:
            registry.mark_completed(discussion_id, "cancelled")
        except Exception:
            logger.exception("Discussion %s failed", discussion_id)
            registry.mark_completed(discussion_id, "error")

    entry.task = asyncio.create_task(_run_and_finalize())

    return CreateDiscussionResponse(
        discussion_id=discussion_id, status="running"
    )


# ── SSE stream ─────────────────────────────────────────────


@router.get("/{discussion_id}/stream")
async def stream_discussion(
    discussion_id: str,
    request: Request,
    user=Depends(require_user_if_db_enabled),
):
    """SSE endpoint — stream real-time discussion events."""
    registry = _get_registry(request)
    entry = registry.get(discussion_id)
    if not entry:
        raise HTTPException(404, "Discussion not found")
    _ensure_discussion_access(entry, user)

    # Find the SSEStreamer on this bus
    streamer = _find_streamer(entry.event_bus)
    if not streamer:
        raise HTTPException(500, "SSE streamer not attached")

    # Parse Last-Event-ID for reconnection replay
    last_id_header = request.headers.get("Last-Event-ID")
    last_id = int(last_id_header) if last_id_header and last_id_header.isdigit() else None

    queue = streamer.create_listener(last_event_id=last_id)

    async def event_generator():
        try:
            while True:
                if await request.is_disconnected():
                    break
                try:
                    payload = await asyncio.wait_for(queue.get(), timeout=30.0)
                except asyncio.TimeoutError:
                    yield {"event": "ping", "data": ""}
                    continue

                if payload is None:
                    # Stream finished
                    break

                yield payload
        finally:
            streamer.remove_listener(queue)

    return EventSourceResponse(event_generator())


# ── Status / detail ────────────────────────────────────────


@router.get("/{discussion_id}", response_model=DiscussionStatusResponse)
async def get_discussion_status(
    discussion_id: str,
    request: Request,
    user=Depends(require_user_if_db_enabled),
):
    """Get current status of a discussion."""
    registry = _get_registry(request)
    entry = registry.get(discussion_id)
    if not entry:
        raise HTTPException(404, "Discussion not found")
    _ensure_discussion_access(entry, user)

    status_snapshot = entry.orchestrator.get_status_snapshot()

    return DiscussionStatusResponse(
        discussion_id=discussion_id,
        question=entry.question,
        status=entry.status,
        personas=entry.persona_ids,
        rounds_completed=status_snapshot["rounds_completed"],
        token_used=status_snapshot["token_used"],
        token_budget=status_snapshot["token_budget"],
    )


# ── Intervene ──────────────────────────────────────────────


@router.post("/{discussion_id}/intervene")
async def intervene(
    discussion_id: str,
    body: InterventionRequest,
    request: Request,
    user=Depends(require_user_if_db_enabled),
):
    """Send a human intervention to an active discussion."""
    registry = _get_registry(request)
    entry = registry.get(discussion_id)
    if not entry:
        raise HTTPException(404, "Discussion not found")
    _ensure_discussion_access(entry, user)
    if entry.status != "running":
        raise HTTPException(409, "Discussion is not running")

    if body.type == "stop":
        await entry.orchestrator.cancel()
    else:
        await entry.orchestrator.intervene(body.content)

    return {"status": "accepted"}


# ── Cancel ─────────────────────────────────────────────────


@router.post("/{discussion_id}/cancel")
async def cancel_discussion(
    discussion_id: str,
    request: Request,
    user=Depends(require_user_if_db_enabled),
):
    """Request graceful cancellation of a running discussion."""
    registry = _get_registry(request)
    entry = registry.get(discussion_id)
    if not entry:
        raise HTTPException(404, "Discussion not found")
    _ensure_discussion_access(entry, user)
    if entry.status != "running":
        raise HTTPException(409, "Discussion is not running")

    await entry.orchestrator.cancel()
    return {"status": "cancelling"}


# ── Helper ─────────────────────────────────────────────────


def _find_streamer(bus: EventBus) -> SSEStreamer | None:
    """Locate the SSEStreamer attached to an EventBus."""
    for listener in bus.get_listeners():
        if isinstance(listener, SSEStreamer):
            return listener
    return None


def _ensure_discussion_access(entry, user) -> None:
    """Enforce discussion ownership when auth is enabled."""
    if user is None:
        return
    if entry.user_id != getattr(user, "id", None):
        raise HTTPException(404, "Discussion not found")
