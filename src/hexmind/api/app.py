"""HexMind API — FastAPI application factory."""

from __future__ import annotations

import logging
import os
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse

from hexmind.api.registry import DiscussionRegistry
from hexmind.api.routes_analytics import router as analytics_router
from hexmind.api.routes_archive_personas import (
    archive_router,
    init_archive_routes,
    init_persona_routes,
    persona_router,
)
from hexmind.api.routes_auth import router as auth_router
from hexmind.api.routes_chat import router as chat_router
from hexmind.api.routes_discussions import init_discussion_routes, router as discussion_router
from hexmind.api.routes_prompts import init_prompt_routes, router as prompt_router
from hexmind.api.routes_billing import router as billing_router
from hexmind.api.routes_clerk_webhooks import router as clerk_webhook_router
from hexmind.api.routes_settings import router as settings_router
from hexmind.api.routes_trial import router as trial_router
from hexmind.api.routes_turnstile import router as turnstile_router
from hexmind.archive.database import close_db, get_session_factory, init_db
# Import side-effect: register trial ORM models on Base.metadata so init_db creates them.
from hexmind.archive import trial_db_models  # noqa: F401
from hexmind.archive.reader import ArchiveReader
from hexmind.archive.search import ArchiveSearch
from hexmind.config import load_config, load_discussion_plan
from hexmind.model_catalog import load_model_catalog
from hexmind.personas.loader import PersonaLoader
from hexmind.prompt_library.loader import PromptLibraryLoader

logger = logging.getLogger(__name__)


def _resolve_frontend_dist_dir() -> Path | None:
    """Resolve a built frontend directory for single-port local serving."""
    configured = os.getenv("HEXMIND_WEB_DIST_DIR")
    repo_root = Path(__file__).resolve().parents[3]
    candidates: list[Path] = []

    if configured:
        candidates.append(Path(configured))

    candidates.extend([
        Path.cwd() / "web" / "dist",
        repo_root / "web" / "dist",
    ])

    for candidate in candidates:
        try:
            resolved = candidate.resolve()
        except OSError:
            continue
        if (resolved / "index.html").exists():
            return resolved
    return None


def _mount_frontend(app: FastAPI) -> None:
    """Serve the built SPA from the API server when available."""
    frontend_dist = _resolve_frontend_dist_dir()
    if frontend_dist is None:
        return

    app.state.frontend_dist_dir = frontend_dist
    index_path = frontend_dist / "index.html"
    logger.info("Serving frontend bundle from %s", frontend_dist)

    @app.get("/", include_in_schema=False)
    async def frontend_index():
        return FileResponse(index_path)

    @app.get("/{full_path:path}", include_in_schema=False)
    async def frontend_spa(full_path: str):
        if full_path.startswith("api/"):
            raise HTTPException(status_code=404, detail="Not found")

        requested = (frontend_dist / full_path).resolve()
        try:
            requested.relative_to(frontend_dist)
        except ValueError as exc:
            raise HTTPException(status_code=404, detail="Not found") from exc

        if full_path and requested.is_file():
            return FileResponse(requested)

        return FileResponse(index_path)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Setup / teardown shared resources."""
    # ── Startup ────────────────────────────────────
    registry = DiscussionRegistry()
    loader = PersonaLoader()
    prompt_loader = PromptLibraryLoader()
    reader = ArchiveReader()
    search = ArchiveSearch()
    app.state.discussion_plan = load_discussion_plan()
    app.state.runtime_config = load_config()
    app.state.model_catalog = load_model_catalog()

    # Initialize database if DATABASE_URL is set
    db_url = os.getenv("DATABASE_URL")
    if db_url:
        await init_db(db_url)
        logger.info("Database initialized: %s", db_url.split("@")[-1] if "@" in db_url else "local")

    # Wire dependencies into route modules
    init_discussion_routes(
        app,
        registry,
        loader,
        get_session_factory() if db_url else None,
    )
    init_archive_routes(app, reader, search)
    init_persona_routes(app, loader)
    init_prompt_routes(app, prompt_loader)

    logger.info("HexMind API started")
    yield

    # ── Shutdown ───────────────────────────────────
    # Cancel any running discussions
    for entry in registry.list_all():
        if entry.task and not entry.task.done():
            entry.task.cancel()

    await close_db()
    logger.info("HexMind API stopped")


def create_app() -> FastAPI:
    """Build and return the FastAPI application."""
    app = FastAPI(
        title="HexMind API",
        version="0.1.0",
        description="Six Hats Multi-Expert AI Decision Engine",
        lifespan=lifespan,
    )

    # CORS — allow Next.js dev server + production domains
    _default_origins = [
        "http://localhost:3000",   # Next.js landing dev
        "http://localhost:5173",   # Vite app dev
        "https://hexmind.ai",
        "https://www.hexmind.ai",
        "https://app.hexmind.ai",
    ]
    _extra = os.environ.get("CORS_ALLOW_ORIGINS", "")
    _cors_origins = _default_origins + [o.strip() for o in _extra.split(",") if o.strip()]

    app.add_middleware(
        CORSMiddleware,
        allow_origins=_cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Mount routers
    app.include_router(discussion_router)
    app.include_router(archive_router)
    app.include_router(persona_router)
    app.include_router(prompt_router)
    app.include_router(auth_router)
    app.include_router(analytics_router)
    app.include_router(settings_router)
    app.include_router(billing_router)
    app.include_router(chat_router)
    app.include_router(trial_router)
    app.include_router(clerk_webhook_router)
    app.include_router(turnstile_router)

    @app.get("/api/health")
    async def health():
        from hexmind.archive.database import _session_factory
        return {"status": "ok", "database": _session_factory is not None}

    _mount_frontend(app)

    return app


# uvicorn entrypoint: `uvicorn hexmind.api.app:app`
app = create_app()
