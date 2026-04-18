"""JIT user provisioning from Clerk claims.

When a request arrives with a valid Clerk JWT for a user who does not yet
exist in our local `users` table, we create the row on the fly (upsert).
This is the fallback for missed webhook deliveries.
"""

from __future__ import annotations

import logging

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from hexmind.archive.db_models import UserDB
from hexmind.auth.clerk_verifier import ClerkClaims, fetch_clerk_user_email

logger = logging.getLogger(__name__)


async def get_or_provision_user(
    session: AsyncSession,
    claims: ClerkClaims,
) -> UserDB:
    """Return the UserDB row for a Clerk subject, creating it if missing.

    Lookup order:
        1. users.clerk_user_id == claims.sub  (normal authenticated path)
        2. users.email == claims.email        (legacy users created via
           local email/password before Clerk integration)
        3. Create a new user row (JIT).
    """
    stmt = select(UserDB).where(UserDB.clerk_user_id == claims.sub)
    result = await session.execute(stmt)
    user = result.scalar_one_or_none()
    if user is not None:
        return user

    # No match on Clerk id. Fetch profile for email + display name.
    email = claims.email
    display_name: str | None = None
    if email is None:
        email, display_name = await fetch_clerk_user_email(claims.sub)

    if email:
        stmt = select(UserDB).where(UserDB.email == email)
        result = await session.execute(stmt)
        legacy = result.scalar_one_or_none()
        if legacy is not None:
            # Link existing local-auth user to Clerk id.
            legacy.clerk_user_id = claims.sub
            await session.flush()
            return legacy

    # Create a brand-new user.
    final_email = email or f"{claims.sub}@clerk.local"
    final_display = display_name or (email.split("@")[0] if email else claims.sub[:20])
    user = UserDB(
        email=final_email,
        display_name=final_display,
        # Clerk owns credentials. Store a marker so verify_password always
        # fails for this user on any legacy /api/auth/login attempt.
        password_hash=f"clerk:{claims.sub}",
        clerk_user_id=claims.sub,
    )
    session.add(user)
    await session.flush()
    logger.info("Provisioned Clerk user %s as local user %s", claims.sub, user.id)
    return user
