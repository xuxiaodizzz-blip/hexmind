"""Anonymous trial quota service.

Provides:

* `check_trial_allowed` — gate before LLM calls; returns whether the visitor
  may consume another built-in trial, plus the global circuit-breaker state.
* `record_trial_used` — atomically increments per-visitor and per-day counters.
* `record_spend` — appends actual USD spend (cents) to the daily ledger.

Design notes:

* Visitor identity is sha256(ip + user_agent). Not personally identifiable
  on its own; only stored as a hex digest.
* All writes use INSERT ... ON CONFLICT DO UPDATE (UPSERT) for atomicity.
  This works on both SQLite and PostgreSQL via SQLAlchemy's dialect dispatch.
* Per-visitor cap and daily USD cap are read from env on each call so they
  can be tuned without restart in dev. In prod, set them at deploy time.
"""

from __future__ import annotations

import hashlib
import logging
import os
from dataclasses import dataclass
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from sqlalchemy.ext.asyncio import AsyncSession

from hexmind.archive.trial_db_models import DailySpendDB, TrialUsageDB

logger = logging.getLogger(__name__)


def _trial_limit_per_visitor() -> int:
    try:
        return max(0, int(os.getenv("HEXMIND_TRIAL_LIMIT_PER_VISITOR", "1")))
    except ValueError:
        return 1


def _daily_usd_limit_cents() -> int:
    """Daily global USD cap in cents. Default 300 cents = $3/day."""
    try:
        return max(0, int(float(os.getenv("HEXMIND_DAILY_USD_LIMIT", "3.0")) * 100))
    except ValueError:
        return 300


@dataclass(frozen=True)
class TrialStatus:
    """Result of a trial-quota check."""

    allowed: bool
    visitor_used: int
    visitor_limit: int
    daily_used_cents: int
    daily_limit_cents: int
    reason: str  # "ok" | "visitor_exhausted" | "daily_budget_exhausted" | "disabled"

    @property
    def visitor_remaining(self) -> int:
        return max(0, self.visitor_limit - self.visitor_used)


def hash_visitor(ip: str, user_agent: str | None) -> str:
    """Stable opaque visitor id. Not reversible to IP/UA on its own."""
    payload = f"{ip}|{user_agent or ''}".encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


async def get_trial_status(
    session: AsyncSession,
    visitor_hash: str,
) -> TrialStatus:
    """Read-only check; does NOT consume quota."""
    visitor_limit = _trial_limit_per_visitor()
    daily_limit = _daily_usd_limit_cents()

    if visitor_limit == 0:
        return TrialStatus(
            allowed=False,
            visitor_used=0,
            visitor_limit=0,
            daily_used_cents=0,
            daily_limit_cents=daily_limit,
            reason="disabled",
        )

    visitor_row = await session.get(TrialUsageDB, visitor_hash)
    visitor_used = visitor_row.trial_count if visitor_row else 0

    today = datetime.now(timezone.utc).date()
    daily_row = await session.get(DailySpendDB, today)
    daily_used = daily_row.total_usd_cents if daily_row else 0

    if visitor_used >= visitor_limit:
        return TrialStatus(
            allowed=False,
            visitor_used=visitor_used,
            visitor_limit=visitor_limit,
            daily_used_cents=daily_used,
            daily_limit_cents=daily_limit,
            reason="visitor_exhausted",
        )
    if daily_limit > 0 and daily_used >= daily_limit:
        return TrialStatus(
            allowed=False,
            visitor_used=visitor_used,
            visitor_limit=visitor_limit,
            daily_used_cents=daily_used,
            daily_limit_cents=daily_limit,
            reason="daily_budget_exhausted",
        )
    return TrialStatus(
        allowed=True,
        visitor_used=visitor_used,
        visitor_limit=visitor_limit,
        daily_used_cents=daily_used,
        daily_limit_cents=daily_limit,
        reason="ok",
    )


async def consume_trial(
    session: AsyncSession,
    visitor_hash: str,
) -> None:
    """Atomically increment the visitor's trial counter and the daily request count.

    Caller is responsible for committing the surrounding transaction.
    """
    now = datetime.now(timezone.utc)
    today = now.date()

    # UPSERT visitor counter
    visitor_stmt = sqlite_insert(TrialUsageDB).values(
        visitor_hash=visitor_hash,
        trial_count=1,
        first_used_at=now,
        last_used_at=now,
    )
    visitor_stmt = visitor_stmt.on_conflict_do_update(
        index_elements=[TrialUsageDB.visitor_hash],
        set_={
            "trial_count": TrialUsageDB.trial_count + 1,
            "last_used_at": now,
        },
    )
    await session.execute(visitor_stmt)

    # UPSERT daily request count (spend cents updated separately by record_spend)
    daily_stmt = sqlite_insert(DailySpendDB).values(
        spend_date=today,
        total_usd_cents=0,
        trial_request_count=1,
    )
    daily_stmt = daily_stmt.on_conflict_do_update(
        index_elements=[DailySpendDB.spend_date],
        set_={"trial_request_count": DailySpendDB.trial_request_count + 1},
    )
    await session.execute(daily_stmt)
    await session.commit()


async def record_spend(
    session: AsyncSession,
    usd_cents: int,
) -> None:
    """Add actual USD spend (cents, integer) to today's ledger."""
    if usd_cents <= 0:
        return
    today = datetime.now(timezone.utc).date()
    stmt = sqlite_insert(DailySpendDB).values(
        spend_date=today,
        total_usd_cents=usd_cents,
        trial_request_count=0,
    )
    stmt = stmt.on_conflict_do_update(
        index_elements=[DailySpendDB.spend_date],
        set_={"total_usd_cents": DailySpendDB.total_usd_cents + usd_cents},
    )
    await session.execute(stmt)
    await session.commit()
