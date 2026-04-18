"""Trial quota and global spend ledger ORM models.

Two tables:

* `trial_usage` — one row per anonymous visitor (identified by sha256(ip+ua)),
  tracks how many built-in free trials they have consumed. Used to gate the
  "1 free trial then BYOK" flow.

* `daily_spend` — one row per UTC date, accumulates total USD spent and trial
  request count across all anonymous traffic. Used as a global circuit
  breaker so a single bad day cannot exhaust the entire $100 budget.

Both tables live in the same SQLAlchemy `Base.metadata` as the rest of the
archive models so `init_db()` creates them automatically.
"""

from __future__ import annotations

from datetime import date, datetime, timezone

from sqlalchemy import Date, DateTime, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from hexmind.archive.db_models import Base


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _utctoday() -> date:
    return datetime.now(timezone.utc).date()


class TrialUsageDB(Base):
    """Per-visitor trial quota counter.

    `visitor_hash` is sha256(ip + user_agent) — opaque, not reversible to PII.
    """

    __tablename__ = "trial_usage"

    visitor_hash: Mapped[str] = mapped_column(String(64), primary_key=True)
    trial_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    first_used_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, nullable=False
    )
    last_used_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, nullable=False
    )


class DailySpendDB(Base):
    """Daily global spend ledger for circuit-breaker enforcement.

    `total_usd_cents` is integer cents to avoid float precision drift.
    """

    __tablename__ = "daily_spend"

    spend_date: Mapped[date] = mapped_column(Date, primary_key=True, default=_utctoday)
    total_usd_cents: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    trial_request_count: Mapped[int] = mapped_column(
        Integer, default=0, nullable=False
    )
