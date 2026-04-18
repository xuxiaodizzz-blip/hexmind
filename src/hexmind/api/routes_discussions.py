"""API routes — discussion lifecycle (create, stream, intervene, cancel)."""

from __future__ import annotations

import asyncio
import logging
from uuid import uuid4

from fastapi import APIRouter, Depends, FastAPI, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from sse_starlette.sse import EventSourceResponse

from hexmind.api.registry import DiscussionRegistry
from hexmind.api.routes_billing import calculate_credits
from hexmind.api.schemas import (
    CreateDiscussionRequest,
    CreateDiscussionResponse,
    DiscussionStatusResponse,
    InterventionRequest,
)
from hexmind.config import load_config, load_discussion_plan
from hexmind.discussion_contract import build_request_config_snapshot
from hexmind.discussion_profiles import (
    DiscussionPlanEnvelope,
    resolve_discussion_profile,
)
from hexmind.api.sse import SSEStreamer
from hexmind.api.trial_gate import commit_trial_consumption, evaluate_trial_gate
from hexmind.api.trial_pricing import usd_cents_for
from hexmind.api.trial_service import record_spend
from hexmind.api.user_credentials import extract_user_credentials
from hexmind.auth.dependencies import get_optional_user_safe, require_user_if_db_enabled
from hexmind.engine.orchestrator import Orchestrator
from hexmind.events.bus import EventBus
from hexmind.events.consumers.archive_writer import ArchiveWriter
from hexmind.events.consumers.db_writer import DBWriter
from hexmind.events.types import EventType
from hexmind.llm.litellm_wrapper import LiteLLMWrapper
from hexmind.model_catalog import ModelCatalog, load_model_catalog
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


def _get_runtime_config(request: Request):
    config = getattr(request.app.state, "runtime_config", None)
    return config or load_config()


def _get_discussion_plan(request: Request) -> DiscussionPlanEnvelope:
    plan = getattr(request.app.state, "discussion_plan", None)
    return plan or load_discussion_plan()


def _get_model_catalog(request: Request) -> ModelCatalog:
    catalog = getattr(request.app.state, "model_catalog", None)
    return catalog or load_model_catalog()


# ── Create discussion ──────────────────────────────────────


@router.post("/", response_model=CreateDiscussionResponse)
async def create_discussion(
    request: Request,
    body: CreateDiscussionRequest,
    user=Depends(get_optional_user_safe),
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

    base_config = _get_runtime_config(request)
    discussion_plan = _get_discussion_plan(request)
    catalog = _get_model_catalog(request)

    config_overrides = body.config.model_dump(exclude_unset=True) if body.config else {}
    selected_model_id = config_overrides.get("selected_model")
    if isinstance(selected_model_id, str) and not selected_model_id.strip():
        selected_model_id = None
    try:
        selected_model = catalog.resolve(selected_model_id)
    except KeyError:
        raise HTTPException(422, f"Unknown selected_model: {selected_model_id}")
    fallback_model = catalog.fallback_for(selected_model.id)
    requested_depth = config_overrides.get("analysis_depth") or base_config.analysis_depth
    profile = resolve_discussion_profile(discussion_plan, requested_depth)

    if len(body.persona_ids) > profile.max_personas:
        raise HTTPException(
            422,
            (
                f"Selected {len(body.persona_ids)} personas but analysis_depth "
                f"'{profile.analysis_depth}' allows at most {profile.max_personas}"
            ),
        )

    requested_execution_cap = config_overrides.get(
        "execution_token_cap",
        profile.execution_token_cap,
    )
    execution_token_cap = min(
        requested_execution_cap,
        discussion_plan.max_execution_token_cap,
    )
    reserve_ratio = (
        profile.finalization_reserve_token_cap / profile.execution_token_cap
        if profile.execution_token_cap > 0
        else 0.20
    )
    finalization_reserve = max(
        1,
        min(
            max(1, execution_token_cap - 1),
            int(round(execution_token_cap * reserve_ratio)),
        ),
    )
    exploration_token_cap = max(1, execution_token_cap - finalization_reserve)
    discussion_max_rounds = min(
        config_overrides.get("discussion_max_rounds", profile.discussion_max_rounds),
        discussion_plan.max_rounds,
    )
    time_budget_seconds = min(
        config_overrides.get("time_budget_seconds", profile.time_budget_seconds),
        discussion_plan.max_time_budget_seconds,
    )

    config = base_config.model_copy(
        update={
            "analysis_depth": profile.analysis_depth,
            "plan_max_personas": discussion_plan.max_personas,
            "plan_execution_token_cap": discussion_plan.max_execution_token_cap,
            "plan_discussion_max_rounds": discussion_plan.max_rounds,
            "plan_time_budget_seconds": discussion_plan.max_time_budget_seconds,
            "plan_max_tree_depth": discussion_plan.max_tree_depth,
            "plan_max_tree_width": discussion_plan.max_tree_width,
            "plan_max_fork_rounds": discussion_plan.max_fork_rounds,
            "resolved_model_slug": selected_model.slug,
            "resolved_fallback_model_slug": fallback_model.slug,
            "selected_model_id": selected_model.id,
            "fallback_model_id": fallback_model.id,
            "execution_token_cap": execution_token_cap,
            "exploration_token_cap": exploration_token_cap,
            "finalization_reserve_token_cap": finalization_reserve,
            "discussion_max_rounds": discussion_max_rounds,
            "time_budget_seconds": time_budget_seconds,
            "max_tree_depth": profile.max_tree_depth,
            "max_tree_width": profile.max_tree_width,
            "max_fork_rounds": profile.max_fork_rounds,
            "degradation_reduced_pct": profile.degradation_reduced_pct,
            "degradation_minimal_pct": profile.degradation_minimal_pct,
            "degradation_forced_pct": profile.degradation_forced_pct,
            "token_warning_pct": profile.degradation_reduced_pct,
            "discussion_locale": config_overrides.get(
                "discussion_locale",
                base_config.discussion_locale,
            ),
        }
    )
    request_config_snapshot = build_request_config_snapshot(
        persona_ids=body.persona_ids,
        selected_model_id=selected_model.id,
        analysis_depth=config.analysis_depth,
        discussion_locale=config.discussion_locale,
        execution_token_cap=config.execution_token_cap,
        discussion_max_rounds=config.discussion_max_rounds,
        time_budget_seconds=config.time_budget_seconds,
    )

    # Create engine components — honor user-supplied BYOK credentials if present
    creds = extract_user_credentials(request)

    # Trial gate: gate before creating any heavy resources
    db_session_factory = _get_db_session_factory(request)
    gate_session = db_session_factory() if db_session_factory is not None else None
    try:
        decision = await evaluate_trial_gate(request, user, gate_session)
    except Exception:
        if gate_session is not None:
            await gate_session.close()
        raise
    # Use credentials from the gate (resolved from headers consistently)
    creds = decision.credentials

    llm = LiteLLMWrapper(
        model=config.resolved_model_slug,
        api_key=creds.api_key,
        api_base=creds.api_base,
    )
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
        request_config_snapshot=request_config_snapshot,
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
            usage = orch.get_billable_usage()
            snapshot = {"token_used": usage.total_tokens}
            credits_used = calculate_credits(
                config.resolved_model_slug,
                input_tokens=usage.input_tokens,
                output_tokens=usage.output_tokens,
            )
            logger.info(
                "Discussion %s finished — tokens: %d, credits: %.1f",
                discussion_id, snapshot.get("token_used", 0), credits_used,
            )
            if orch.last_run_status == NodeStatus.CANCELLED:
                registry.mark_completed(
                    discussion_id,
                    "cancelled",
                    termination_reason=orch.last_terminal_reason,
                )
            elif orch.has_partial_verdict():
                registry.mark_completed(
                    discussion_id,
                    "partial",
                    termination_reason=orch.last_terminal_reason,
                )
            else:
                registry.mark_completed(
                    discussion_id,
                    "converged",
                    termination_reason=orch.last_terminal_reason,
                )
        except asyncio.CancelledError:
            registry.mark_completed(
                discussion_id,
                "cancelled",
                termination_reason="task_cancelled",
            )
        except Exception as exc:
            logger.exception("Discussion %s failed", discussion_id)
            registry.mark_completed(
                discussion_id,
                "error",
                termination_reason=str(exc) or "uncaught_error",
            )
        finally:
            # Bookkeeping: increment trial counter + record real USD spend.
            # Only meaningful when this request was served via the trial gate
            # (authenticated and BYOK requests don't consume the shared budget).
            try:
                if decision.mode == "trial" and gate_session is not None:
                    try:
                        usage = orch.get_billable_usage()
                        cents = usd_cents_for(
                            config.resolved_model_slug,
                            input_tokens=usage.input_tokens,
                            output_tokens=usage.output_tokens,
                        )
                        await record_spend(gate_session, cents)
                    except Exception:
                        logger.exception(
                            "Discussion %s: failed to record trial USD spend",
                            discussion_id,
                        )
                await commit_trial_consumption(decision, gate_session)
            finally:
                if gate_session is not None:
                    await gate_session.close()

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
        run_state=entry.run_state,
        completion_status=entry.completion_status,
        termination_reason=entry.termination_reason,
        status=entry.status,
        personas=entry.persona_ids,
        rounds_completed=status_snapshot["rounds_completed"],
        token_used=status_snapshot["token_used"],
        execution_token_cap=status_snapshot.get(
            "execution_token_cap",
            status_snapshot.get("token_budget", 0),
        ),
        exploration_token_cap=status_snapshot.get("exploration_token_cap", 0),
        finalization_reserve_token_cap=status_snapshot.get(
            "finalization_reserve_token_cap",
            0,
        ),
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
    if not entry.is_running:
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
    if not entry.is_running:
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
