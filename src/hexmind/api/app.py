"""HexMind API — FastAPI application factory."""

from __future__ import annotations

import logging
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from hexmind.api.registry import DiscussionRegistry
from hexmind.api.routes_analytics import router as analytics_router
from hexmind.api.routes_archive_personas import (
    archive_router,
    init_archive_routes,
    init_persona_routes,
    persona_router,
)
from hexmind.api.routes_auth import router as auth_router
from hexmind.api.routes_discussions import init_discussion_routes, router as discussion_router
from hexmind.api.routes_prompts import init_prompt_routes, router as prompt_router
from hexmind.archive.database import close_db, get_session_factory, init_db
from hexmind.archive.reader import ArchiveReader
from hexmind.archive.search import ArchiveSearch
from hexmind.personas.loader import PersonaLoader
from hexmind.prompt_library.loader import PromptLibraryLoader

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Setup / teardown shared resources."""
    # ── Startup ────────────────────────────────────
    registry = DiscussionRegistry()
    loader = PersonaLoader()
    prompt_loader = PromptLibraryLoader()
    reader = ArchiveReader()
    search = ArchiveSearch()

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

    # CORS — allow Next.js dev server
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:3000", "http://localhost:5173"],
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

    @app.get("/api/health")
    async def health():
        from hexmind.archive.database import _session_factory
        return {"status": "ok", "database": _session_factory is not None}

    return app


# uvicorn entrypoint: `uvicorn hexmind.api.app:app`
app = create_app()
