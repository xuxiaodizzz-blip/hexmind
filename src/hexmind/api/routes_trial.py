"""Trial quota status endpoint for the frontend BYOK flow."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from hexmind.api.trial_gate import _client_ip
from hexmind.api.trial_service import get_trial_status, hash_visitor
from hexmind.archive.database import get_session

router = APIRouter(prefix="/api/trial", tags=["trial"])


@router.get("/status")
async def trial_status_endpoint(
    request: Request,
    session: AsyncSession = Depends(get_session),
):
    visitor_hash = hash_visitor(
        _client_ip(request),
        request.headers.get("user-agent"),
    )
    status = await get_trial_status(session, visitor_hash)
    return {
        "allowed": status.allowed,
        "reason": status.reason,
        "visitor_used": status.visitor_used,
        "visitor_limit": status.visitor_limit,
        "visitor_remaining": status.visitor_remaining,
        "daily_used_cents": status.daily_used_cents,
        "daily_limit_cents": status.daily_limit_cents,
    }
