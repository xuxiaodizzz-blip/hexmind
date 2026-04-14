"""Auth API routes: register, login, profile, team management."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from hexmind.api.schemas import (
    AddMemberRequest,
    AuthResponse,
    CreateTeamRequest,
    LoginRequest,
    RegisterRequest,
    TeamMemberInfo,
    TeamSummary,
    UserProfile,
)
from hexmind.archive.database import get_session
from hexmind.archive.db_models import UserDB
from hexmind.archive.repository import TeamRepository, UserRepository
from hexmind.auth.dependencies import get_current_user, require_team_access
from hexmind.auth.service import create_access_token, hash_password, verify_password

router = APIRouter(prefix="/api", tags=["auth"])


# ---------------------------------------------------------------------------
# Auth
# ---------------------------------------------------------------------------


@router.post("/auth/register", response_model=AuthResponse, status_code=201)
async def register(
    body: RegisterRequest, session: AsyncSession = Depends(get_session)
) -> AuthResponse:
    repo = UserRepository(session)
    existing = await repo.get_by_email(body.email)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Registration failed",
        )
    pw_hash = hash_password(body.password)
    user = await repo.create(
        email=body.email,
        display_name=body.display_name,
        password_hash=pw_hash,
    )
    await session.commit()
    token = create_access_token(user.id)
    return AuthResponse(
        access_token=token, user_id=user.id, display_name=user.display_name
    )


@router.post("/auth/login", response_model=AuthResponse)
async def login(
    body: LoginRequest, session: AsyncSession = Depends(get_session)
) -> AuthResponse:
    repo = UserRepository(session)
    user = await repo.get_by_email(body.email)
    if user is None or not verify_password(body.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )
    await repo.update_last_login(user.id)
    await session.commit()
    token = create_access_token(user.id)
    return AuthResponse(
        access_token=token, user_id=user.id, display_name=user.display_name
    )


@router.get("/auth/me", response_model=UserProfile)
async def me(user: UserDB = Depends(get_current_user)) -> UserProfile:
    return UserProfile(
        id=user.id,
        email=user.email,
        display_name=user.display_name,
        created_at=user.created_at.isoformat() if user.created_at else "",
    )


# ---------------------------------------------------------------------------
# Teams
# ---------------------------------------------------------------------------


@router.post("/teams", response_model=TeamSummary, status_code=201)
async def create_team(
    body: CreateTeamRequest,
    user: UserDB = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> TeamSummary:
    repo = TeamRepository(session)
    team = await repo.create(name=body.name, owner_id=user.id)
    await session.commit()
    return TeamSummary(id=team.id, name=team.name, role="owner", member_count=1)


@router.get("/teams", response_model=list[TeamSummary])
async def list_teams(
    user: UserDB = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> list[TeamSummary]:
    repo = TeamRepository(session)
    teams = await repo.list_for_user(user.id)
    result: list[TeamSummary] = []
    for team in teams:
        role = await repo.get_member_role(team.id, user.id)
        result.append(
            TeamSummary(
                id=team.id,
                name=team.name,
                role=role or "member",
                member_count=len(team.members) if team.members else 0,
            )
        )
    return result


@router.post("/teams/{team_id}/members", response_model=TeamMemberInfo, status_code=201)
async def add_member(
    team_id: str,
    body: AddMemberRequest,
    user: UserDB = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> TeamMemberInfo:
    await require_team_access(team_id, user, session, min_role="admin")
    user_repo = UserRepository(session)
    target = await user_repo.get_by_email(body.email)
    if target is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found by email",
        )
    team_repo = TeamRepository(session)
    existing_role = await team_repo.get_member_role(team_id, target.id)
    if existing_role:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="User is already a team member",
        )
    await team_repo.add_member(team_id=team_id, user_id=target.id, role=body.role)
    await session.commit()
    return TeamMemberInfo(
        user_id=target.id,
        email=target.email,
        display_name=target.display_name,
        role=body.role,
    )


@router.delete("/teams/{team_id}/members/{member_user_id}", status_code=204)
async def remove_member(
    team_id: str,
    member_user_id: str,
    user: UserDB = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> None:
    await require_team_access(team_id, user, session, min_role="admin")
    team_repo = TeamRepository(session)
    removed = await team_repo.remove_member(team_id=team_id, user_id=member_user_id)
    if not removed:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot remove owner or member not found",
        )
    await session.commit()


@router.get("/teams/{team_id}/members", response_model=list[TeamMemberInfo])
async def list_members(
    team_id: str,
    user: UserDB = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> list[TeamMemberInfo]:
    await require_team_access(team_id, user, session, min_role="viewer")
    team_repo = TeamRepository(session)
    team = await team_repo.get_by_id(team_id)
    if team is None:
        raise HTTPException(status_code=404, detail="Team not found")
    return [
        TeamMemberInfo(
            user_id=m.user_id,
            email=m.user.email if m.user else "",
            display_name=m.user.display_name if m.user else "",
            role=m.role,
        )
        for m in (team.members or [])
    ]
