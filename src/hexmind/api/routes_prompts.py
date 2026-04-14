"""API routes for the normalized prompt library."""

from __future__ import annotations

from fastapi import APIRouter, Depends, FastAPI, HTTPException, Request

from hexmind.api.schemas import PromptDetail, PromptSummary
from hexmind.auth.dependencies import require_user_if_db_enabled
from hexmind.prompt_library.loader import PromptLibraryLoader

router = APIRouter(prefix="/api/prompts", tags=["prompts"])


def init_prompt_routes(app: FastAPI, loader: PromptLibraryLoader) -> None:
    app.state.prompt_library_loader = loader


@router.get("/", response_model=list[PromptSummary])
async def list_prompts(
    request: Request,
    position: str | None = None,
    domain: str | None = None,
    kind: str | None = None,
    hat: str | None = None,
    status: str | None = None,
    user=Depends(require_user_if_db_enabled),
):
    """List normalized prompt library entries."""
    loader = _get_prompt_loader(request)
    if loader is None:
        raise RuntimeError("PromptLibraryLoader not initialized")

    assets = loader.load_all()
    if position:
        assets = [asset for asset in assets if asset.position == position]
    if domain:
        assets = [asset for asset in assets if asset.domain == domain]
    if kind:
        assets = [asset for asset in assets if asset.kind == kind]
    if hat:
        assets = [asset for asset in assets if hat in {item.value for item in asset.applicable_hats}]
    if status:
        assets = [asset for asset in assets if asset.status == status]

    return [
        PromptSummary(
            id=asset.id,
            name=asset.name,
            position=asset.position,
            domain=asset.domain,
            kind=asset.kind,
            hat=asset.hat.value if asset.hat else None,
            hat_context=asset.hat_context,
            applicable_hats=[hat.value for hat in asset.applicable_hats],
            status=asset.status,
            source=asset.source,
            description=asset.description,
        )
        for asset in assets
    ]


@router.get("/{prompt_id}", response_model=PromptDetail)
async def get_prompt(
    prompt_id: str,
    request: Request,
    user=Depends(require_user_if_db_enabled),
):
    """Get a full prompt library entry by ID."""
    loader = _get_prompt_loader(request)
    if loader is None:
        raise RuntimeError("PromptLibraryLoader not initialized")

    try:
        asset = loader.load(prompt_id)
    except FileNotFoundError:
        raise HTTPException(404, f"Prompt not found: {prompt_id}")

    return PromptDetail(
        id=asset.id,
        name=asset.name,
        position=asset.position,
        domain=asset.domain,
        kind=asset.kind,
        hat=asset.hat.value if asset.hat else None,
        hat_context=asset.hat_context,
        applicable_hats=[hat.value for hat in asset.applicable_hats],
        status=asset.status,
        source=asset.source,
        description=asset.description,
        prompt=asset.prompt,
        prompt_mode=asset.prompt_mode,
        tags=asset.tags,
        source_title=asset.source_title,
        source_path=asset.source_path,
    )


def _get_prompt_loader(request: Request) -> PromptLibraryLoader | None:
    return getattr(request.app.state, "prompt_library_loader", None)
