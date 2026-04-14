"""Discussion configuration."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, field_validator


class InteractionMode(BaseModel):
    """How the user interacts with the discussion."""

    mode: Literal["auto", "review", "interactive"] = "auto"


class DegradationLevel(BaseModel):
    """Current budget degradation state."""

    level: Literal["normal", "reduced", "minimal", "forced_conclude"] = "normal"


class DiscussionConfig(BaseModel):
    """Full discussion configuration."""

    # Round limits
    max_rounds: int = 12
    convergence_threshold: float = 0.8
    convergence_consecutive: int = 2
    max_tree_depth: int = 3
    max_tree_width: int = 3
    max_fork_rounds: int = 3

    # Budget
    token_budget: int = 50_000
    token_warning_pct: float = 0.8
    time_budget_seconds: float = 300.0

    # LLM
    default_model: str = "gpt-4o"
    fallback_model: str = "gpt-4o-mini"

    # Validation
    max_validation_retries: int = 1

    # Output
    archive_dir: str = "discussion_archive"
    locale: Literal["zh", "en"] = "zh"

    @field_validator("max_rounds")
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

    @field_validator("token_budget")
    @classmethod
    def token_budget_positive(cls, v: int) -> int:
        if v < 1:
            raise ValueError("token_budget must be >= 1")
        return v

    @field_validator("token_warning_pct")
    @classmethod
    def token_warning_pct_range(cls, v: float) -> float:
        if not 0.0 < v < 1.0:
            raise ValueError("token_warning_pct must be in (0, 1)")
        return v

    @field_validator("time_budget_seconds")
    @classmethod
    def time_budget_positive(cls, v: float) -> float:
        if v <= 0:
            raise ValueError("time_budget_seconds must be > 0")
        return v

    @field_validator("max_tree_depth", "max_tree_width")
    @classmethod
    def tree_limits_positive(cls, v: int) -> int:
        if v < 1:
            raise ValueError("tree dimension limits must be >= 1")
        return v

    @field_validator("max_validation_retries")
    @classmethod
    def retries_non_negative(cls, v: int) -> int:
        if v < 0:
            raise ValueError("max_validation_retries must be >= 0")
        return v
