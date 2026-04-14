"""API routes — archive (list, detail, export) and personas (list, detail, create)."""

from __future__ import annotations

import logging
from typing import Literal

from fastapi import APIRouter, Depends, FastAPI, HTTPException, Request
from fastapi.responses import PlainTextResponse

from hexmind.api.schemas import (
    ArchiveListResponse,
    ArchiveSummary,
    CreatePersonaRequest,
    PersonaDetail,
    PersonaSummary,
)
from hexmind.archive.reader import ArchiveReader
from hexmind.archive.search import ArchiveSearch
from hexmind.auth.dependencies import require_user_if_db_enabled
from hexmind.personas.loader import PersonaLoader

logger = logging.getLogger(__name__)

# ── Archive routes ─────────────────────────────────────────

archive_router = APIRouter(prefix="/api/archive", tags=["archive"])


def init_archive_routes(
    app: FastAPI,
    reader: ArchiveReader,
    search: ArchiveSearch,
) -> None:
    app.state.archive_reader = reader
    app.state.archive_search = search


@archive_router.get("/", response_model=ArchiveListResponse)
async def list_archives(
    request: Request,
    query: str | None = None,
    limit: int = 20,
    offset: int = 0,
    user=Depends(require_user_if_db_enabled),
):
    """List or search discussion archives."""
    limit = min(limit, 100)  # Enforce upper bound
    reader = _get_archive_reader(request)
    if reader is None:
        raise RuntimeError("ArchiveReader not initialized")

    if query:
        search = _get_archive_search(request)
        if search is None:
            raise RuntimeError("ArchiveSearch not initialized")
        result = search.search(query, max_results=limit)
        hits = [hit for hit in result.hits if _can_access_archive(hit.entry, user)]
        items = [
            ArchiveSummary(
                id=hit.entry.dir_name,
                question=hit.entry.meta.get("question", ""),
                created_at=hit.entry.meta.get("created_at", ""),
                status=hit.entry.meta.get("status", "unknown"),
                personas=hit.entry.meta.get("personas", []),
                verdict=hit.entry.meta.get("verdict"),
                confidence=hit.entry.meta.get("confidence"),
            )
            for hit in hits
        ]
        return ArchiveListResponse(total=len(hits), items=items)

    entries = [entry for entry in reader.list_entries() if _can_access_archive(entry, user)]
    sliced = entries[offset : offset + limit]
    items = [
        ArchiveSummary(
            id=e.dir_name,
            question=e.meta.get("question", ""),
            created_at=e.meta.get("created_at", ""),
            status=e.meta.get("status", "unknown"),
            personas=e.meta.get("personas", []),
            verdict=e.meta.get("verdict"),
            confidence=e.meta.get("confidence"),
        )
        for e in sliced
    ]
    return ArchiveListResponse(total=len(entries), items=items)


@archive_router.get("/{archive_id}")
async def get_archive(
    archive_id: str,
    request: Request,
    user=Depends(require_user_if_db_enabled),
):
    """Get full archive detail (markdown + summary)."""
    reader = _get_archive_reader(request)
    if reader is None:
        raise RuntimeError("ArchiveReader not initialized")

    entry = reader.get_entry(archive_id)
    if entry is None:
        raise HTTPException(404, "Archive not found")
    if not _can_access_archive(entry, user):
        raise HTTPException(404, "Archive not found")

    return {
        "id": archive_id,
        "meta": entry.meta,
        "discussion_md": entry.discussion_md,
        "summary": entry.summary.model_dump() if entry.summary else None,
    }


@archive_router.get("/{archive_id}/export")
async def export_archive(
    archive_id: str,
    request: Request,
    format: Literal["markdown", "json"] = "markdown",
    user=Depends(require_user_if_db_enabled),
):
    """Export archive as markdown or JSON."""
    reader = _get_archive_reader(request)
    if reader is None:
        raise RuntimeError("ArchiveReader not initialized")

    entry = reader.get_entry(archive_id)
    if entry is None:
        raise HTTPException(404, "Archive not found")
    if not _can_access_archive(entry, user):
        raise HTTPException(404, "Archive not found")

    if format == "json":
        if entry.summary:
            return entry.summary.model_dump()
        return {}
    else:
        return PlainTextResponse(
            entry.discussion_md,
            media_type="text/markdown; charset=utf-8",
        )


# ── Persona routes ─────────────────────────────────────────

persona_router = APIRouter(prefix="/api/personas", tags=["personas"])


def init_persona_routes(app: FastAPI, loader: PersonaLoader) -> None:
    app.state.persona_loader = loader


@persona_router.get("/", response_model=list[PersonaSummary])
async def list_personas(
    request: Request,
    domain: str | None = None,
    user=Depends(require_user_if_db_enabled),
):
    """List all available personas, optionally filtered by domain."""
    loader = _get_persona_loader(request)
    if loader is None:
        raise RuntimeError("PersonaLoader not initialized")

    all_personas = loader.load_all()
    if domain:
        all_personas = [p for p in all_personas if p.domain == domain]

    return [
        PersonaSummary(
            id=p.id, name=p.name, domain=p.domain, description=p.description
        )
        for p in sorted(all_personas, key=lambda x: x.id)
    ]


@persona_router.get("/{persona_id}", response_model=PersonaDetail)
async def get_persona(
    persona_id: str,
    request: Request,
    user=Depends(require_user_if_db_enabled),
):
    """Get full persona detail."""
    loader = _get_persona_loader(request)
    if loader is None:
        raise RuntimeError("PersonaLoader not initialized")

    try:
        p = loader.load(persona_id)
    except FileNotFoundError:
        raise HTTPException(404, f"Persona not found: {persona_id}")

    return PersonaDetail(
        id=p.id,
        name=p.name,
        domain=p.domain,
        description=p.description,
        prompt=p.prompt,
    )


@persona_router.post("/", response_model=PersonaDetail, status_code=201)
async def create_persona(
    body: CreatePersonaRequest,
    request: Request,
    user=Depends(require_user_if_db_enabled),
):
    """Create a custom persona (saved to personas/<domain>/)."""
    loader = _get_persona_loader(request)
    if loader is None:
        raise RuntimeError("PersonaLoader not initialized")

    if user is not None:
        raise HTTPException(
            403,
            "Custom persona creation is only available in offline mode",
        )

    # Check for duplicate
    existing = loader.load_all()
    if any(p.id == body.id for p in existing):
        raise HTTPException(409, f"Persona already exists: {body.id}")

    from hexmind.models.persona import Persona

    persona = Persona.model_validate(body.model_dump())
    loader.save(persona)

    return PersonaDetail(
        id=persona.id,
        name=persona.name,
        domain=persona.domain,
        description=persona.description,
        prompt=persona.prompt,
    )


def _can_access_archive(entry, user) -> bool:
    """Archive access is unrestricted in offline mode and owner-scoped in DB mode."""
    if user is None:
        return True
    return entry.meta.get("user_id") == getattr(user, "id", None)


def _get_archive_reader(request: Request) -> ArchiveReader | None:
    return getattr(request.app.state, "archive_reader", None)


def _get_archive_search(request: Request) -> ArchiveSearch | None:
    return getattr(request.app.state, "archive_search", None)


def _get_persona_loader(request: Request) -> PersonaLoader | None:
    return getattr(request.app.state, "persona_loader", None)
