"""Auth service: JWT token creation/verification and password hashing."""

from __future__ import annotations

import os
from datetime import datetime, timedelta, timezone

import bcrypt
import jwt

_ALGORITHM = "HS256"
_ACCESS_TOKEN_EXPIRE_HOURS = 24


def _get_secret() -> str:
    secret = os.getenv("JWT_SECRET")
    if not secret:
        raise RuntimeError("JWT_SECRET environment variable is required")
    return secret


# ---------------------------------------------------------------------------
# Password hashing
# ---------------------------------------------------------------------------


def hash_password(plain: str) -> str:
    return bcrypt.hashpw(plain.encode(), bcrypt.gensalt()).decode()


def verify_password(plain: str, hashed: str) -> bool:
    return bcrypt.checkpw(plain.encode(), hashed.encode())


# ---------------------------------------------------------------------------
# JWT tokens
# ---------------------------------------------------------------------------


def create_access_token(
    user_id: str, *, expires_hours: int = _ACCESS_TOKEN_EXPIRE_HOURS
) -> str:
    now = datetime.now(timezone.utc)
    payload = {
        "sub": user_id,
        "iat": now,
        "exp": now + timedelta(hours=expires_hours),
    }
    return jwt.encode(payload, _get_secret(), algorithm=_ALGORITHM)


def decode_access_token(token: str) -> dict:
    """Decode and verify a JWT access token. Raises jwt.PyJWTError on failure."""
    return jwt.decode(token, _get_secret(), algorithms=[_ALGORITHM])
