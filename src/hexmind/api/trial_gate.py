"""Trial-quota gate for anonymous LLM-consuming endpoints.

Decision matrix:

| Authenticated? | BYOK header? | Trial remaining? | Global budget OK? | Outcome |
|----------------|--------------|------------------|-------------------|---------|
| yes            | *            | *                | *                 | authenticated |
| no             | yes          | *                | *                 | byok    |
| no             | no           | yes              | yes               | trial   |
| no             | no           | no               | *                 | exhausted_byok_required (402) |
| no             | no           | yes              | no                | global_budget_exhausted (402) |

`mode == "trial"` is the only branch that needs a quota write afterwards;
caller MUST `await consume_trial()` once the LLM call has been dispatched
(we increment optimistically — on user-side abort the count is still spent,
which is acceptable because the LLM cost may already have been incurred).
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Literal

from fastapi import HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession

from hexmind.api.trial_service import (
    TrialStatus,
    consume_trial,
    get_trial_status,
    hash_visitor,
)
from hexmind.api.user_credentials import UserLLMCredentials, extract_user_credentials

logger = logging.getLogger(__name__)

GateMode = Literal["authenticated", "byok", "trial"]


@dataclass(frozen=True)
class TrialGateDecision:
    """Outcome of the trial gate. Only `mode == "trial"` requires a follow-up consume call."""

    mode: GateMode
    visitor_hash: str | None
    credentials: UserLLMCredentials
    trial_status: TrialStatus | None


def _client_ip(request: Request) -> str:
    """Extract client IP, honoring X-Forwarded-For when behind a reverse proxy."""
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    if request.client is None:
        return "unknown"
    return request.client.host or "unknown"


async def evaluate_trial_gate(
    request: Request,
    user,  # UserDB | None — typed loosely to avoid circular import
    session: AsyncSession | None,
) -> TrialGateDecision:
    """Decide which credential path serves this request.

    Raises HTTPException(402) when neither built-in trial nor BYOK is available.
    """
    creds = extract_user_credentials(request)

    if user is not None:
        return TrialGateDecision(
            mode="authenticated",
            visitor_hash=None,
            credentials=creds,
            trial_status=None,
        )

    if creds.is_present:
        return TrialGateDecision(
            mode="byok",
            visitor_hash=None,
            credentials=creds,
            trial_status=None,
        )

    # Anonymous + no BYOK → check trial quota
    if session is None:
        # No DB configured — disable gating entirely (local single-user mode)
        return TrialGateDecision(
            mode="trial",
            visitor_hash=None,
            credentials=creds,
            trial_status=None,
        )

    visitor_hash = hash_visitor(
        _client_ip(request),
        request.headers.get("user-agent"),
    )
    status = await get_trial_status(session, visitor_hash)

    if not status.allowed:
        if status.reason == "daily_budget_exhausted":
            raise HTTPException(
                status_code=402,
                detail={
                    "code": "daily_budget_exhausted",
                    "message": (
                        "The shared free-trial budget for today is used up. "
                        "Please add your own API key or come back tomorrow."
                    ),
                    "trial_status": {
                        "visitor_used": status.visitor_used,
                        "visitor_limit": status.visitor_limit,
                    },
                },
            )
        raise HTTPException(
            status_code=402,
            detail={
                "code": "trial_exhausted",
                "message": (
                    "Your free trial has been used. "
                    "Add your own OpenAI / Requesty API key to keep using HexMind."
                ),
                "trial_status": {
                    "visitor_used": status.visitor_used,
                    "visitor_limit": status.visitor_limit,
                },
            },
        )

    return TrialGateDecision(
        mode="trial",
        visitor_hash=visitor_hash,
        credentials=creds,
        trial_status=status,
    )


async def commit_trial_consumption(
    decision: TrialGateDecision,
    session: AsyncSession | None,
) -> None:
    """Increment quota counters after a successful trial dispatch."""
    if decision.mode != "trial" or decision.visitor_hash is None or session is None:
        return
    try:
        await consume_trial(session, decision.visitor_hash)
    except Exception:  # never let bookkeeping kill the request
        logger.exception("Failed to record trial consumption")
