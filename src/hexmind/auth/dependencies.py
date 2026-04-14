"""Auth dependencies for FastAPI: current user, team access checks."""

from __future__ import annotations

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

import jwt as pyjwt

from hexmind.archive.database import get_session, get_session_factory
from hexmind.archive.db_models import UserDB
from hexmind.archive.repository import TeamRepository, UserRepository
from hexmind.auth.service import decode_access_token

_bearer_scheme = HTTPBearer(auto_error=False)


async def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer_scheme),
    session: AsyncSession = Depends(get_session),
) -> UserDB:
    """FastAPI dependency: extract and verify the current user from Bearer token."""
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing authorization header",
        )
    try:
        payload = decode_access_token(credentials.credentials)
    except pyjwt.PyJWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
        )

    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token payload",
        )

    repo = UserRepository(session)
    user = await repo.get_by_id(user_id)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
        )
    return user


async def get_optional_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer_scheme),
    session: AsyncSession = Depends(get_session),
) -> UserDB | None:
    """Optional auth: returns None if no token provided."""
    if credentials is None:
        return None
    try:
        return await get_current_user(credentials, session)
    except HTTPException:
        return None


async def get_optional_user_safe(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer_scheme),
) -> UserDB | None:
    """Optional auth that gracefully handles missing database.

    Returns None if no token, no DB, or invalid token.
    Safe for routes that must work with or without database.
    """
    if credentials is None:
        return None
    try:
        from hexmind.archive.database import get_session_factory
        factory = get_session_factory()
    except RuntimeError:
        return None
    async with factory() as session:
        try:
            return await get_current_user(credentials, session)
        except HTTPException:
            return None


def is_database_enabled() -> bool:
    """Return whether database-backed auth is currently available."""
    try:
        get_session_factory()
    except RuntimeError:
        return False
    return True


async def require_user_if_db_enabled(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer_scheme),
) -> UserDB | None:
    """Require a valid user whenever the database is enabled.

    In offline/demo mode without a database, returns None so unauthenticated
    discussion flows continue to work.
    """
    if not is_database_enabled():
        return None

    factory = get_session_factory()
    async with factory() as session:
        return await get_current_user(credentials, session)


async def require_team_access(
    team_id: str,
    user: UserDB,
    session: AsyncSession,
    *,
    min_role: str = "member",
) -> str:
    """Check that user has at least min_role in the team. Returns the role."""
    role_hierarchy = {"viewer": 0, "member": 1, "admin": 2, "owner": 3}
    repo = TeamRepository(session)
    role = await repo.get_member_role(team_id, user.id)
    if role is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not a member of this team",
        )
    if role_hierarchy.get(role, 0) < role_hierarchy.get(min_role, 0):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Requires at least '{min_role}' role",
        )
    return role
