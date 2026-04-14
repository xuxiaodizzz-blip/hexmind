"""Global configuration loader: .env + environment variables."""

from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

from hexmind.models.config import DiscussionConfig


def load_config(env_file: str | None = None) -> DiscussionConfig:
    """Load configuration from .env file and environment variables.

    Priority: explicit env vars > .env file > defaults.
    """
    if env_file:
        load_dotenv(env_file)
    else:
        # Search for .env in current dir and parents
        load_dotenv()

    return DiscussionConfig(
        max_rounds=int(os.getenv("HEXMIND_MAX_ROUNDS", "12")),
        convergence_threshold=float(os.getenv("HEXMIND_CONVERGENCE_THRESHOLD", "0.8")),
        convergence_consecutive=int(os.getenv("HEXMIND_CONVERGENCE_CONSECUTIVE", "2")),
        max_tree_depth=int(os.getenv("HEXMIND_MAX_TREE_DEPTH", "3")),
        max_tree_width=int(os.getenv("HEXMIND_MAX_TREE_WIDTH", "3")),
        max_fork_rounds=int(os.getenv("HEXMIND_MAX_FORK_ROUNDS", "3")),
        token_budget=int(os.getenv("HEXMIND_TOKEN_BUDGET", "50000")),
        token_warning_pct=float(os.getenv("HEXMIND_TOKEN_WARNING_PCT", "0.8")),
        time_budget_seconds=float(os.getenv("HEXMIND_TIME_BUDGET", "300.0")),
        default_model=os.getenv("HEXMIND_MODEL", "gpt-4o"),
        fallback_model=os.getenv("HEXMIND_FALLBACK_MODEL", "gpt-4o-mini"),
        max_validation_retries=int(os.getenv("HEXMIND_MAX_VALIDATION_RETRIES", "1")),
        archive_dir=os.getenv("HEXMIND_ARCHIVE_DIR", "discussion_archive"),
        locale=os.getenv("HEXMIND_LOCALE", "zh"),  # type: ignore[arg-type]
    )
