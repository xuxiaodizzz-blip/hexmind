"""Global configuration loader: .env + environment variables."""

from __future__ import annotations

import os

from dotenv import load_dotenv

from hexmind.discussion_profiles import (
    AnalysisDepth,
    DiscussionPlanEnvelope,
    resolve_discussion_profile,
)
from hexmind.model_catalog import load_model_catalog
from hexmind.models.config import DiscussionConfig


def _first_env(*names: str, default: str) -> str:
    """Return the first non-empty environment variable from the given names."""
    for name in names:
        value = os.getenv(name)
        if value:
            return value
    return default


def _load_env(env_file: str | None = None) -> None:
    """Load dotenv values before reading environment-backed config."""

    if env_file:
        load_dotenv(env_file)
    else:
        load_dotenv()


def load_discussion_plan(env_file: str | None = None) -> DiscussionPlanEnvelope:
    """Load plan ceilings used to resolve runtime depth presets."""

    _load_env(env_file)

    return DiscussionPlanEnvelope(
        default_analysis_depth=_first_env(
            "HEXMIND_DEFAULT_ANALYSIS_DEPTH",
            default="standard",
        ),  # type: ignore[arg-type]
        max_personas=int(os.getenv("HEXMIND_MAX_PERSONAS", "5")),
        max_execution_token_cap=int(
            _first_env(
                "HEXMIND_EXECUTION_TOKEN_CAP",
                "HEXMIND_TOKEN_BUDGET",
                default="50000",
            )
        ),
        max_rounds=int(os.getenv("HEXMIND_MAX_ROUNDS", "12")),
        max_time_budget_seconds=float(os.getenv("HEXMIND_TIME_BUDGET", "300.0")),
        max_tree_depth=int(os.getenv("HEXMIND_MAX_TREE_DEPTH", "3")),
        max_tree_width=int(os.getenv("HEXMIND_MAX_TREE_WIDTH", "3")),
        max_fork_rounds=int(os.getenv("HEXMIND_MAX_FORK_ROUNDS", "3")),
    )


def load_config(env_file: str | None = None) -> DiscussionConfig:
    """Load default runtime config from env-backed plan ceilings.

    Priority: explicit env vars > .env file > defaults.
    """
    _load_env(env_file)

    catalog = load_model_catalog(env_file)
    plan = load_discussion_plan(env_file)
    profile = resolve_discussion_profile(plan, plan.default_analysis_depth)
    default_model = catalog.resolve().slug
    fallback_model = catalog.fallback_for(catalog.default_model_id).slug

    return DiscussionConfig(
        analysis_depth=profile.analysis_depth,
        plan_max_personas=plan.max_personas,
        plan_execution_token_cap=plan.max_execution_token_cap,
        plan_discussion_max_rounds=plan.max_rounds,
        plan_time_budget_seconds=plan.max_time_budget_seconds,
        plan_max_tree_depth=plan.max_tree_depth,
        plan_max_tree_width=plan.max_tree_width,
        plan_max_fork_rounds=plan.max_fork_rounds,
        discussion_max_rounds=profile.discussion_max_rounds,
        convergence_threshold=float(os.getenv("HEXMIND_CONVERGENCE_THRESHOLD", "0.8")),
        convergence_consecutive=int(os.getenv("HEXMIND_CONVERGENCE_CONSECUTIVE", "2")),
        max_tree_depth=profile.max_tree_depth,
        max_tree_width=profile.max_tree_width,
        max_fork_rounds=profile.max_fork_rounds,
        execution_token_cap=profile.execution_token_cap,
        exploration_token_cap=profile.exploration_token_cap,
        finalization_reserve_token_cap=profile.finalization_reserve_token_cap,
        degradation_reduced_pct=profile.degradation_reduced_pct,
        degradation_minimal_pct=profile.degradation_minimal_pct,
        degradation_forced_pct=profile.degradation_forced_pct,
        token_warning_pct=profile.degradation_reduced_pct,
        time_budget_seconds=profile.time_budget_seconds,
        resolved_model_slug=default_model,
        resolved_fallback_model_slug=fallback_model,
        selected_model_id=catalog.default_model_id,
        fallback_model_id=catalog.fallback_model_id or catalog.default_model_id,
        max_validation_retries=int(os.getenv("HEXMIND_MAX_VALIDATION_RETRIES", "1")),
        archive_dir=os.getenv("HEXMIND_ARCHIVE_DIR", "discussion_archive"),
        discussion_locale=_first_env(
            "HEXMIND_DISCUSSION_LOCALE",
            "HEXMIND_LOCALE",
            default="zh",
        ),  # type: ignore[arg-type]
    )
