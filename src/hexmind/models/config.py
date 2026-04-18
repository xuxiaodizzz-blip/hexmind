"""Discussion configuration."""

from __future__ import annotations

from typing import Literal

from pydantic import (
    AliasChoices,
    BaseModel,
    ConfigDict,
    Field,
    field_validator,
    model_validator,
)


class InteractionMode(BaseModel):
    """How the user interacts with the discussion."""

    mode: Literal["auto", "review", "interactive"] = "auto"


class DegradationLevel(BaseModel):
    """Current budget degradation state."""

    level: Literal["normal", "reduced", "minimal", "forced_conclude"] = "normal"


class DiscussionConfig(BaseModel):
    """Full discussion configuration."""

    model_config = ConfigDict(populate_by_name=True)

    # Plan / preset envelope
    analysis_depth: Literal["quick", "standard", "deep"] = "standard"
    plan_max_personas: int = 5
    plan_execution_token_cap: int = 50_000
    plan_discussion_max_rounds: int = 12
    plan_time_budget_seconds: float = 300.0
    plan_max_tree_depth: int = 3
    plan_max_tree_width: int = 3
    plan_max_fork_rounds: int = 3

    # Round limits
    discussion_max_rounds: int = Field(
        default=12,
        validation_alias=AliasChoices("discussion_max_rounds", "max_rounds"),
    )
    convergence_threshold: float = 0.8
    convergence_consecutive: int = 2
    max_tree_depth: int = 3
    max_tree_width: int = 3
    max_fork_rounds: int = 3

    # Budget
    execution_token_cap: int = Field(
        default=50_000,
        validation_alias=AliasChoices("execution_token_cap", "token_budget"),
    )
    exploration_token_cap: int | None = None
    finalization_reserve_token_cap: int | None = None
    degradation_reduced_pct: float = 0.70
    degradation_minimal_pct: float = 0.85
    degradation_forced_pct: float = 0.95
    token_warning_pct: float = 0.8
    time_budget_seconds: float = 300.0

    # LLM
    resolved_model_slug: str = Field(
        default="gpt-4o",
        validation_alias=AliasChoices("resolved_model_slug", "default_model"),
    )
    resolved_fallback_model_slug: str = Field(
        default="gpt-4o-mini",
        validation_alias=AliasChoices(
            "resolved_fallback_model_slug",
            "fallback_model",
        ),
    )
    selected_model_id: str | None = Field(
        default=None,
        validation_alias=AliasChoices(
            "selected_model_id",
            "selected_model_alias",
            "selected_model",
        ),
    )
    fallback_model_id: str | None = Field(
        default=None,
        validation_alias=AliasChoices("fallback_model_id", "fallback_model_alias"),
    )

    # Validation
    max_validation_retries: int = 1

    # Output
    archive_dir: str = "discussion_archive"
    discussion_locale: Literal["zh", "en"] = Field(
        default="zh",
        validation_alias=AliasChoices("discussion_locale", "locale"),
    )

    @property
    def max_rounds(self) -> int:
        return self.discussion_max_rounds

    @property
    def token_budget(self) -> int:
        return self.execution_token_cap

    @property
    def default_model(self) -> str:
        return self.resolved_model_slug

    @property
    def fallback_model(self) -> str:
        return self.resolved_fallback_model_slug

    @property
    def selected_model_alias(self) -> str | None:
        return self.selected_model_id

    @property
    def fallback_model_alias(self) -> str | None:
        return self.fallback_model_id

    @property
    def max_personas(self) -> int:
        return self.plan_max_personas

    @field_validator("discussion_max_rounds")
    @classmethod
    def max_rounds_positive(cls, v: int) -> int:
        if v < 1:
            raise ValueError("max_rounds must be >= 1")
        return v

    @field_validator("convergence_threshold")
    @classmethod
    def convergence_threshold_range(cls, v: float) -> float:
        if not 0.0 < v <= 1.0:
            raise ValueError("convergence_threshold must be in (0, 1]")
        return v

    @field_validator("execution_token_cap")
    @classmethod
    def token_budget_positive(cls, v: int) -> int:
        if v < 1:
            raise ValueError("token_budget must be >= 1")
        return v

    @field_validator(
        "plan_max_personas",
        "plan_execution_token_cap",
        "plan_discussion_max_rounds",
        "plan_max_tree_depth",
        "plan_max_tree_width",
    )
    @classmethod
    def plan_limits_positive(cls, v: int) -> int:
        if v < 1:
            raise ValueError("plan limits must be >= 1")
        return v

    @field_validator("plan_max_fork_rounds")
    @classmethod
    def plan_fork_rounds_non_negative(cls, v: int) -> int:
        if v < 0:
            raise ValueError("plan_max_fork_rounds must be >= 0")
        return v

    @field_validator("exploration_token_cap", "finalization_reserve_token_cap")
    @classmethod
    def optional_budget_positive(cls, v: int | None) -> int | None:
        if v is not None and v < 1:
            raise ValueError("budget segments must be >= 1 when provided")
        return v

    @field_validator("token_warning_pct")
    @classmethod
    def token_warning_pct_range(cls, v: float) -> float:
        if not 0.0 < v < 1.0:
            raise ValueError("token_warning_pct must be in (0, 1)")
        return v

    @field_validator(
        "degradation_reduced_pct",
        "degradation_minimal_pct",
        "degradation_forced_pct",
    )
    @classmethod
    def degradation_threshold_range(cls, v: float) -> float:
        if not 0.0 < v < 1.0:
            raise ValueError("degradation thresholds must be in (0, 1)")
        return v

    @field_validator("time_budget_seconds")
    @classmethod
    def time_budget_positive(cls, v: float) -> float:
        if v <= 0:
            raise ValueError("time_budget_seconds must be > 0")
        return v

    @field_validator("plan_time_budget_seconds")
    @classmethod
    def plan_time_budget_positive(cls, v: float) -> float:
        if v <= 0:
            raise ValueError("plan_time_budget_seconds must be > 0")
        return v

    @field_validator("max_tree_depth", "max_tree_width")
    @classmethod
    def tree_limits_positive(cls, v: int) -> int:
        if v < 1:
            raise ValueError("tree dimension limits must be >= 1")
        return v

    @field_validator("convergence_consecutive")
    @classmethod
    def convergence_consecutive_positive(cls, v: int) -> int:
        if v < 1:
            raise ValueError("convergence_consecutive must be >= 1")
        return v

    @field_validator("max_fork_rounds")
    @classmethod
    def max_fork_rounds_positive(cls, v: int) -> int:
        if v < 0:
            raise ValueError("max_fork_rounds must be >= 0")
        return v

    @field_validator("max_validation_retries")
    @classmethod
    def retries_non_negative(cls, v: int) -> int:
        if v < 0:
            raise ValueError("max_validation_retries must be >= 0")
        return v

    @model_validator(mode="after")
    def finalize_budget_splits(self) -> "DiscussionConfig":
        if self.exploration_token_cap is None and self.finalization_reserve_token_cap is None:
            reserve = max(1, int(round(self.execution_token_cap * 0.20)))
            if reserve >= self.execution_token_cap:
                reserve = max(1, self.execution_token_cap - 1)
            self.finalization_reserve_token_cap = reserve
            self.exploration_token_cap = max(1, self.execution_token_cap - reserve)
        elif self.exploration_token_cap is None and self.finalization_reserve_token_cap is not None:
            self.exploration_token_cap = max(
                1,
                self.execution_token_cap - self.finalization_reserve_token_cap,
            )
        elif self.finalization_reserve_token_cap is None and self.exploration_token_cap is not None:
            self.finalization_reserve_token_cap = max(
                1,
                self.execution_token_cap - self.exploration_token_cap,
            )

        assert self.exploration_token_cap is not None
        assert self.finalization_reserve_token_cap is not None

        if (
            self.exploration_token_cap + self.finalization_reserve_token_cap
            > self.execution_token_cap
        ):
            raise ValueError(
                "exploration_token_cap + finalization_reserve_token_cap must not exceed execution_token_cap"
            )

        if not (
            self.degradation_reduced_pct
            < self.degradation_minimal_pct
            < self.degradation_forced_pct
        ):
            raise ValueError(
                "degradation thresholds must increase in reduced < minimal < forced order"
            )

        return self
