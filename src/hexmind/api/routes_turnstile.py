"""
Cloudflare Turnstile server-side verification.

Route: POST /api/turnstile/verify
Used by the sign-up form to prove the user is human before creating an account.

Environment variable required:
    CLOUDFLARE_TURNSTILE_SECRET_KEY — from https://dash.cloudflare.com → Turnstile

Docs: https://developers.cloudflare.com/turnstile/get-started/server-side-validation/
"""

import os
import logging
from typing import Any

import httpx
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

logger = logging.getLogger(__name__)

router = APIRouter(tags=["turnstile"])

_VERIFY_URL = "https://challenges.cloudflare.com/turnstile/v1/siteverify"
_SECRET_KEY = os.environ.get("CLOUDFLARE_TURNSTILE_SECRET_KEY", "")


class TurnstileRequest(BaseModel):
    token: str


class TurnstileResponse(BaseModel):
    success: bool


@router.post("/api/turnstile/verify", response_model=TurnstileResponse)
async def verify_turnstile(body: TurnstileRequest) -> Any:
    """
    Verify a Cloudflare Turnstile challenge token.

    Returns {success: true} on pass, raises 400 on failure.
    If no secret key is configured (local dev), always returns success.
    """
    if not _SECRET_KEY:
        # Local dev / CI: Turnstile is not configured — always pass
        logger.debug("Turnstile secret key not set; skipping verification (dev mode)")
        return TurnstileResponse(success=True)

    if not body.token:
        raise HTTPException(status_code=400, detail="Missing Turnstile token")

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.post(
                _VERIFY_URL,
                data={"secret": _SECRET_KEY, "response": body.token},
            )
        result = resp.json()
    except Exception as exc:
        logger.error("Turnstile verification request failed: %s", exc)
        raise HTTPException(status_code=502, detail="Turnstile verification failed") from exc

    if not result.get("success"):
        codes = result.get("error-codes", [])
        logger.warning("Turnstile challenge failed: %s", codes)
        raise HTTPException(status_code=400, detail="Turnstile challenge failed")

    return TurnstileResponse(success=True)
