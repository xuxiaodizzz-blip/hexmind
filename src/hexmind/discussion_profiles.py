"""Analysis-depth presets and runtime profile resolution."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

AnalysisDepth = Literal["quick", "standard", "deep"]


class DiscussionPlanEnvelope(BaseModel):
    """Current plan or environment ceilings for a single discussion."""

    default_analysis_depth: AnalysisDepth = "standard"
    max_personas: int = 5
    max_execution_token_cap: int = 50_000
    max_rounds: int = 12
    max_time_budget_seconds: float = 300.0
    max_tree_depth: int = 3
    max_tree_width: int = 3
    max_fork_rounds: int = 3


class AnalysisDepthPreset(BaseModel):
    """Preset policy before plan ceilings are applied."""

    id: AnalysisDepth
    execution_ratio: float
    rounds_ratio: float
    time_ratio: float
    finalization_reserve_ratio: float
    persona_limit: int | None = None
    max_tree_depth: int | None = None
    max_tree_width: int | None = None
    max_fork_rounds: int | None = None
    degradation_reduced_pct: float
    degradation_minimal_pct: float
    degradation_forced_pct: float


class DiscussionRuntimeProfile(BaseModel):
    """Resolved execution parameters for one discussion."""

    analysis_depth: AnalysisDepth
    max_personas: int
    execution_token_cap: int
    exploration_token_cap: int
    finalization_reserve_token_cap: int
    discussion_max_rounds: int
    time_budget_seconds: float
    max_tree_depth: int
    max_tree_width: int
    max_fork_rounds: int
    degradation_reduced_pct: float
    degradation_minimal_pct: float
    degradation_forced_pct: float

    @property
    def supports_fork(self) -> bool:
        return (
            self.max_tree_depth > 1
            and self.max_tree_width > 1
            and self.max_fork_rounds > 0
        )


class AnalysisDepthOptionSummary(BaseModel):
    """Frontend-safe summary for one preset after plan ceilings are applied."""

    id: AnalysisDepth
    max_personas: int
    execution_token_cap: int
    exploration_token_cap: int
    finalization_reserve_token_cap: int
    discussion_max_rounds: int
    time_budget_seconds: int
    supports_fork: bool


_PRESETS: dict[AnalysisDepth, AnalysisDepthPreset] = {
    "quick": AnalysisDepthPreset(
        id="quick",
        execution_ratio=0.40,
        rounds_ratio=0.50,
        time_ratio=0.50,
        finalization_reserve_ratio=0.30,
        persona_limit=2,
        max_tree_depth=1,
        max_tree_width=1,
        max_fork_rounds=1,
        degradation_reduced_pct=0.55,
        degradation_minimal_pct=0.75,
        degradation_forced_pct=0.90,
    ),
    "standard": AnalysisDepthPreset(
        id="standard",
        execution_ratio=0.70,
        rounds_ratio=0.75,
        time_ratio=0.75,
        finalization_reserve_ratio=0.20,
        persona_limit=4,
        max_tree_depth=2,
        max_tree_width=2,
        max_fork_rounds=2,
        degradation_reduced_pct=0.70,
        degradation_minimal_pct=0.85,
        degradation_forced_pct=0.95,
    ),
    "deep": AnalysisDepthPreset(
        id="deep",
        execution_ratio=1.00,
        rounds_ratio=1.00,
        time_ratio=1.00,
        finalization_reserve_ratio=0.15,
        persona_limit=None,
        max_tree_depth=None,
        max_tree_width=None,
        max_fork_rounds=None,
        degradation_reduced_pct=0.80,
        degradation_minimal_pct=0.92,
        degradation_forced_pct=0.98,
    ),
}


def get_depth_preset(depth: AnalysisDepth) -> AnalysisDepthPreset:
    """Return a validated preset definition."""

    return _PRESETS[depth]


def resolve_discussion_profile(
    envelope: DiscussionPlanEnvelope,
    analysis_depth: AnalysisDepth | None = None,
) -> DiscussionRuntimeProfile:
    """Resolve one preset into concrete execution parameters."""

    preset = get_depth_preset(analysis_depth or envelope.default_analysis_depth)
    execution_token_cap = _scaled_int(
        envelope.max_execution_token_cap,
        preset.execution_ratio,
        minimum=1,
    )
    finalization_reserve_token_cap = _scaled_int(
        execution_token_cap,
        preset.finalization_reserve_ratio,
        minimum=1,
        maximum=max(1, execution_token_cap - 1),
    )
    exploration_token_cap = max(
        1,
        execution_token_cap - finalization_reserve_token_cap,
    )

    return DiscussionRuntimeProfile(
        analysis_depth=preset.id,
        max_personas=min(
            envelope.max_personas,
            preset.persona_limit or envelope.max_personas,
        ),
        execution_token_cap=execution_token_cap,
        exploration_token_cap=exploration_token_cap,
        finalization_reserve_token_cap=finalization_reserve_token_cap,
        discussion_max_rounds=_scaled_int(
            envelope.max_rounds,
            preset.rounds_ratio,
            minimum=1,
        ),
        time_budget_seconds=float(
            _scaled_int(
                int(envelope.max_time_budget_seconds),
                preset.time_ratio,
                minimum=60,
            )
        ),
        max_tree_depth=min(
            envelope.max_tree_depth,
            preset.max_tree_depth or envelope.max_tree_depth,
        ),
        max_tree_width=min(
            envelope.max_tree_width,
            preset.max_tree_width or envelope.max_tree_width,
        ),
        max_fork_rounds=min(
            envelope.max_fork_rounds,
            preset.max_fork_rounds or envelope.max_fork_rounds,
        ),
        degradation_reduced_pct=preset.degradation_reduced_pct,
        degradation_minimal_pct=preset.degradation_minimal_pct,
        degradation_forced_pct=preset.degradation_forced_pct,
    )


def build_depth_option_summaries(
    envelope: DiscussionPlanEnvelope,
) -> list[AnalysisDepthOptionSummary]:
    """Return all preset summaries after applying current plan ceilings."""

    summaries: list[AnalysisDepthOptionSummary] = []
    for depth in ("quick", "standard", "deep"):
        profile = resolve_discussion_profile(envelope, depth)
        summaries.append(
            AnalysisDepthOptionSummary(
                id=profile.analysis_depth,
                max_personas=profile.max_personas,
                execution_token_cap=profile.execution_token_cap,
                exploration_token_cap=profile.exploration_token_cap,
                finalization_reserve_token_cap=profile.finalization_reserve_token_cap,
                discussion_max_rounds=profile.discussion_max_rounds,
                time_budget_seconds=int(profile.time_budget_seconds),
                supports_fork=profile.supports_fork,
            )
        )
    return summaries


def _scaled_int(
    value: int,
    ratio: float,
    *,
    minimum: int,
    maximum: int | None = None,
) -> int:
    scaled = max(minimum, int(round(value * ratio)))
    if maximum is not None:
        return min(maximum, scaled)
    return scaled
