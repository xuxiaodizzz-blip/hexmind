"""Analytics API routes: dashboard summary and persona stats."""

from __future__ import annotations

from typing import Literal

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from hexmind.api.schemas import AnalyticsSummaryResponse, PersonaStatItem
from hexmind.archive.database import get_session
from hexmind.archive.db_models import UserDB
from hexmind.archive.repository import AnalyticsRepository
from hexmind.auth.dependencies import get_current_user, require_team_access

router = APIRouter(prefix="/api/analytics", tags=["analytics"])


@router.get("/summary", response_model=AnalyticsSummaryResponse)
async def analytics_summary(
    team_id: str | None = Query(default=None),
    user: UserDB = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> AnalyticsSummaryResponse:
    if team_id:
        await require_team_access(team_id, user, session, min_role="viewer")
    repo = AnalyticsRepository(session)
    data = await repo.summary(user_id=user.id, team_id=team_id)
    return AnalyticsSummaryResponse(**data)


@router.get("/personas", response_model=list[PersonaStatItem])
async def persona_stats(
    team_id: str | None = Query(default=None),
    user: UserDB = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> list[PersonaStatItem]:
    if team_id:
        await require_team_access(team_id, user, session, min_role="viewer")
    repo = AnalyticsRepository(session)
    stats = await repo.persona_stats(user_id=user.id, team_id=team_id)
    return [PersonaStatItem(**s) for s in stats]
