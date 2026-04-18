"""Clerk JWT verifier.

Verifies session JWTs issued by Clerk using JWKS (RS256).
Caches JWKS for 10 minutes to avoid hitting Clerk on every request.

Clerk session JWT claims (what we use):
    sub       Clerk user id (user_xxxxxxxxxxxx)
    iss       https://<clerk-domain>.clerk.accounts.dev  or custom domain
    azp       Allowed frontend origin (optional check)
    exp/iat   Standard JWT timing
    email     Primary email (if template includes it)

Reference:
    https://clerk.com/docs/backend-requests/resources/session-tokens
"""

from __future__ import annotations

import logging
import os
import time
from dataclasses import dataclass
from typing import Any

import httpx
import jwt as pyjwt
from jwt import PyJWKClient

logger = logging.getLogger(__name__)


class ClerkAuthError(Exception):
    """Raised when a Clerk JWT cannot be verified."""


@dataclass(frozen=True)
class ClerkClaims:
    """Validated claims extracted from a Clerk session JWT."""

    sub: str  # Clerk user_id
    email: str | None
    issuer: str
    session_id: str | None = None


# Module-level cache for the JWKS client (singleton).
_jwks_client: PyJWKClient | None = None
_cached_issuer: str | None = None


def _issuer() -> str:
    issuer = os.getenv("CLERK_JWT_ISSUER")
    if issuer:
        return issuer.rstrip("/")
    # Derive from publishable key if not explicitly set.
    # pk_test_<base64(domain.clerk.accounts.dev$)> — we do not decode here to
    # keep things simple; require CLERK_JWT_ISSUER in env for production.
    raise ClerkAuthError(
        "CLERK_JWT_ISSUER environment variable is required when "
        "HEXMIND_AUTH_PROVIDER=clerk (e.g. https://teaching-catfish-43.clerk.accounts.dev)"
    )


def _jwks_url() -> str:
    return f"{_issuer()}/.well-known/jwks.json"


def get_jwks_client() -> PyJWKClient:
    """Return a cached PyJWKClient. Re-creates on issuer change."""
    global _jwks_client, _cached_issuer
    issuer = _issuer()
    if _jwks_client is None or _cached_issuer != issuer:
        _jwks_client = PyJWKClient(_jwks_url(), cache_keys=True, lifespan=600)
        _cached_issuer = issuer
    return _jwks_client


def verify_clerk_jwt(token: str) -> ClerkClaims:
    """Verify a Clerk session JWT.

    Raises ClerkAuthError if the token is invalid, expired, or has a bad issuer.
    Returns the validated subject + optional email.
    """
    expected_issuer = _issuer()
    try:
        signing_key = get_jwks_client().get_signing_key_from_jwt(token).key
    except pyjwt.PyJWKClientError as exc:
        raise ClerkAuthError(f"Unable to fetch Clerk JWKS: {exc}") from exc

    try:
        payload: dict[str, Any] = pyjwt.decode(
            token,
            signing_key,
            algorithms=["RS256"],
            issuer=expected_issuer,
            # Clerk session JWTs do not set `aud` by default; leave it off.
            options={"verify_aud": False, "require": ["exp", "iat", "sub", "iss"]},
        )
    except pyjwt.ExpiredSignatureError as exc:
        raise ClerkAuthError("Clerk token expired") from exc
    except pyjwt.InvalidIssuerError as exc:
        raise ClerkAuthError("Clerk token issuer mismatch") from exc
    except pyjwt.PyJWTError as exc:
        raise ClerkAuthError(f"Clerk token verification failed: {exc}") from exc

    sub = payload.get("sub")
    if not isinstance(sub, str) or not sub:
        raise ClerkAuthError("Clerk token missing 'sub' claim")

    # Email may come from a custom JWT template. If the user didn't configure
    # one, we'll fetch via Clerk Backend API at provisioning time.
    email = payload.get("email")
    if email is not None and not isinstance(email, str):
        email = None

    return ClerkClaims(
        sub=sub,
        email=email,
        issuer=expected_issuer,
        session_id=payload.get("sid") if isinstance(payload.get("sid"), str) else None,
    )


async def fetch_clerk_user_email(clerk_user_id: str) -> tuple[str | None, str | None]:
    """Fetch primary email + display name for a Clerk user via Backend API.

    Returns (email, display_name). Either may be None if the API call fails or
    the user has no primary email.

    Used when the session JWT does not embed email (default Clerk JWT template).
    """
    secret = os.getenv("CLERK_SECRET_KEY")
    if not secret:
        logger.warning("CLERK_SECRET_KEY not set; cannot fetch user profile")
        return None, None

    url = f"https://api.clerk.com/v1/users/{clerk_user_id}"
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.get(url, headers={"Authorization": f"Bearer {secret}"})
        if resp.status_code != 200:
            logger.warning(
                "Clerk Backend API returned %s for user %s",
                resp.status_code,
                clerk_user_id,
            )
            return None, None
        data = resp.json()
    except httpx.HTTPError as exc:
        logger.warning("Clerk Backend API call failed: %s", exc)
        return None, None

    primary_email_id = data.get("primary_email_address_id")
    email = None
    for addr in data.get("email_addresses", []) or []:
        if addr.get("id") == primary_email_id:
            email = addr.get("email_address")
            break

    first = (data.get("first_name") or "").strip()
    last = (data.get("last_name") or "").strip()
    display_name = (
        f"{first} {last}".strip()
        or data.get("username")
        or (email.split("@")[0] if email else None)
    )
    return email, display_name
