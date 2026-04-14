"""Event type definitions and event data model."""

from __future__ import annotations

from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class EventType(str, Enum):
    # Lifecycle
    DISCUSSION_STARTED = "discussion_started"
    CONCLUSION = "conclusion"
    DISCUSSION_CANCELLED = "discussion_cancelled"

    # Round-level
    BLUE_HAT_DECISION = "blue_hat_decision"
    ROUND_STARTED = "round_started"
    ROUND_COMPLETED = "round_completed"
    PANELIST_OUTPUT = "panelist_output"

    # Validation
    VALIDATION_RESULT = "validation_result"

    # Tree
    FORK_CREATED = "fork_created"
    SUB_CONCLUSION = "sub_conclusion"

    # Budget / compression
    BUDGET_WARNING = "budget_warning"
    DEGRADATION_CHANGED = "degradation_changed"
    CONTEXT_COMPRESSED = "context_compressed"

    # Error
    ERROR = "error"


class Event(BaseModel):
    """A single event emitted by the engine."""

    type: EventType
    data: dict[str, Any] = Field(default_factory=dict)
