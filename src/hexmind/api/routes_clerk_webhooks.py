"""Clerk webhook receiver.

Clerk sends webhooks via Svix. Each request carries three headers:
    svix-id, svix-timestamp, svix-signature.

We verify HMAC-SHA256 against CLERK_WEBHOOK_SECRET (base64-encoded after
the 'whsec_' prefix) and handle these event types:
    user.created  → insert local UserDB row
    user.updated  → update email/display_name
    user.deleted  → soft detach (clear clerk_user_id); we keep history.

Reference:
    https://docs.svix.com/receiving/verifying-payloads/how-manual
    https://clerk.com/docs/webhooks/sync-data
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import logging
import os
import time
from typing import Any

from fastapi import APIRouter, HTTPException, Request, status
from sqlalchemy import select

from hexmind.archive.database import get_session_factory
from hexmind.archive.db_models import UserDB

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/webhooks", tags=["webhooks"])

# Svix sends events at most ~5 minutes old; reject anything older (replay guard).
_MAX_SKEW_SECONDS = 300


def _webhook_secret_bytes() -> bytes:
    secret = os.getenv("CLERK_WEBHOOK_SECRET")
    if not secret:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Clerk webhook not configured",
        )
    # Clerk/Svix secret is "whsec_<base64>"; strip the prefix before decoding.
    if secret.startswith("whsec_"):
        secret = secret[len("whsec_") :]
    try:
        return base64.b64decode(secret)
    except (ValueError, base64.binascii.Error) as exc:  # type: ignore[attr-defined]
        logger.error("CLERK_WEBHOOK_SECRET is not valid base64: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Clerk webhook secret malformed",
        ) from exc


def _verify_svix_signature(
    svix_id: str,
    svix_timestamp: str,
    svix_signature: str,
    body: bytes,
) -> None:
    """Constant-time verification of the Svix HMAC header."""
    try:
        ts = int(svix_timestamp)
    except ValueError as exc:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "bad svix-timestamp") from exc

    now = int(time.time())
    if abs(now - ts) > _MAX_SKEW_SECONDS:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "webhook timestamp skew")

    secret = _webhook_secret_bytes()
    signed_content = f"{svix_id}.{svix_timestamp}.".encode() + body
    expected = base64.b64encode(
        hmac.new(secret, signed_content, hashlib.sha256).digest()
    ).decode()

    # Header is "v1,<sig> v1,<sig2> ..." — any matching version is acceptable.
    for segment in svix_signature.split(" "):
        if not segment.startswith("v1,"):
            continue
        received = segment[3:]
        if hmac.compare_digest(received, expected):
            return
    raise HTTPException(status.HTTP_401_UNAUTHORIZED, "invalid svix signature")


def _extract_email_and_name(data: dict[str, Any]) -> tuple[str | None, str | None]:
    primary_id = data.get("primary_email_address_id")
    email: str | None = None
    for addr in data.get("email_addresses", []) or []:
        if addr.get("id") == primary_id:
            email = addr.get("email_address")
            break
    first = (data.get("first_name") or "").strip()
    last = (data.get("last_name") or "").strip()
    display = (
        f"{first} {last}".strip()
        or data.get("username")
        or (email.split("@")[0] if email else None)
    )
    return email, display


@router.post("/clerk", status_code=status.HTTP_204_NO_CONTENT)
async def clerk_webhook(request: Request) -> None:
    svix_id = request.headers.get("svix-id", "")
    svix_timestamp = request.headers.get("svix-timestamp", "")
    svix_signature = request.headers.get("svix-signature", "")
    if not (svix_id and svix_timestamp and svix_signature):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "missing svix headers")

    body = await request.body()
    _verify_svix_signature(svix_id, svix_timestamp, svix_signature, body)

    try:
        payload = request.headers.get("content-type", "").lower()
        if "application/json" not in payload:
            raise HTTPException(status.HTTP_415_UNSUPPORTED_MEDIA_TYPE)
        import json

        event = json.loads(body.decode("utf-8") or "{}")
    except (ValueError, UnicodeDecodeError) as exc:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "bad JSON body") from exc

    event_type = event.get("type")
    data = event.get("data") or {}
    clerk_user_id = data.get("id")

    if not isinstance(clerk_user_id, str) or not clerk_user_id:
        # Not a user event we care about; ACK.
        return

    try:
        factory = get_session_factory()
    except RuntimeError:
        logger.warning("Received Clerk webhook but DB is not configured")
        return

    async with factory() as session:
        if event_type in {"user.created", "user.updated"}:
            email, display = _extract_email_and_name(data)
            stmt = select(UserDB).where(UserDB.clerk_user_id == clerk_user_id)
            result = await session.execute(stmt)
            user = result.scalar_one_or_none()
            if user is None and email:
                # Link an existing local user by email if present.
                stmt = select(UserDB).where(UserDB.email == email)
                result = await session.execute(stmt)
                user = result.scalar_one_or_none()

            if user is None:
                user = UserDB(
                    email=email or f"{clerk_user_id}@clerk.local",
                    display_name=display or clerk_user_id[:20],
                    password_hash=f"clerk:{clerk_user_id}",
                    clerk_user_id=clerk_user_id,
                )
                session.add(user)
            else:
                user.clerk_user_id = clerk_user_id
                if email:
                    user.email = email
                if display:
                    user.display_name = display
            await session.commit()
            logger.info("Clerk webhook %s synced user %s", event_type, clerk_user_id)

        elif event_type == "user.deleted":
            stmt = select(UserDB).where(UserDB.clerk_user_id == clerk_user_id)
            result = await session.execute(stmt)
            user = result.scalar_one_or_none()
            if user is not None:
                user.clerk_user_id = None
                await session.commit()
                logger.info("Clerk webhook detached user %s", clerk_user_id)
        else:
            logger.debug("Ignoring Clerk webhook event type: %s", event_type)
