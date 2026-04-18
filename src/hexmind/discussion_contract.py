"""Shared helpers for discussion request/runtime snapshots."""

from __future__ import annotations

from typing import Any

from hexmind.models.config import DiscussionConfig

SNAPSHOT_NAMESPACE_KEYS = (
    "request_config_snapshot",
    "runtime_config_snapshot",
    "migration_metadata",
)


def build_request_config_snapshot(
    *,
    persona_ids: list[str],
    selected_model_id: str | None,
    analysis_depth: str,
    discussion_locale: str,
    execution_token_cap: int,
    discussion_max_rounds: int,
    time_budget_seconds: float,
) -> dict[str, Any]:
    """Capture the user's requested discussion inputs."""
    return {
        "persona_ids": list(persona_ids),
        "selected_model_id": selected_model_id,
        "analysis_depth": analysis_depth,
        "discussion_locale": discussion_locale,
        "execution_token_cap": execution_token_cap,
        "discussion_max_rounds": discussion_max_rounds,
        "time_budget_seconds": time_budget_seconds,
    }


def build_runtime_config_snapshot(config: DiscussionConfig) -> dict[str, Any]:
    """Capture the resolved runtime execution parameters."""
    return {
        "analysis_depth": config.analysis_depth,
        "plan_max_personas": config.plan_max_personas,
        "plan_execution_token_cap": config.plan_execution_token_cap,
        "plan_discussion_max_rounds": config.plan_discussion_max_rounds,
        "plan_time_budget_seconds": config.plan_time_budget_seconds,
        "plan_max_tree_depth": config.plan_max_tree_depth,
        "plan_max_tree_width": config.plan_max_tree_width,
        "plan_max_fork_rounds": config.plan_max_fork_rounds,
        "discussion_max_rounds": config.discussion_max_rounds,
        "convergence_threshold": config.convergence_threshold,
        "convergence_consecutive": config.convergence_consecutive,
        "max_tree_depth": config.max_tree_depth,
        "max_tree_width": config.max_tree_width,
        "max_fork_rounds": config.max_fork_rounds,
        "execution_token_cap": config.execution_token_cap,
        "exploration_token_cap": config.exploration_token_cap,
        "finalization_reserve_token_cap": config.finalization_reserve_token_cap,
        "degradation_reduced_pct": config.degradation_reduced_pct,
        "degradation_minimal_pct": config.degradation_minimal_pct,
        "degradation_forced_pct": config.degradation_forced_pct,
        "token_warning_pct": config.token_warning_pct,
        "time_budget_seconds": config.time_budget_seconds,
        "resolved_model_slug": config.resolved_model_slug,
        "resolved_fallback_model_slug": config.resolved_fallback_model_slug,
        "selected_model_id": config.selected_model_id,
        "fallback_model_id": config.fallback_model_id,
        "discussion_locale": config.discussion_locale,
        "max_validation_retries": config.max_validation_retries,
        "archive_dir": config.archive_dir,
    }


def normalize_discussion_config_snapshot(
    config: dict[str, Any] | None,
) -> dict[str, Any]:
    """Ensure persisted discussion config uses explicit namespace buckets."""
    if not config:
        return {
            "request_config_snapshot": {},
            "runtime_config_snapshot": {},
            "migration_metadata": {},
        }

    if any(key in config for key in SNAPSHOT_NAMESPACE_KEYS):
        normalized = dict(config)
        normalized.setdefault("request_config_snapshot", {})
        normalized.setdefault("runtime_config_snapshot", {})
        normalized.setdefault("migration_metadata", {})
        return normalized

    return {
        "request_config_snapshot": {},
        "runtime_config_snapshot": dict(config),
        "migration_metadata": {},
    }
