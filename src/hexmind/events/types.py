"""Event type definitions and event data model."""

from __future__ import annotations

from enum import Enum
from typing import Any, TypeVar

from pydantic import AliasChoices, BaseModel, ConfigDict, Field, ValidationError

from hexmind.models.hat import HatColor
from hexmind.models.llm import TokenUsage
from hexmind.models.round import OutputItem

PayloadT = TypeVar("PayloadT", bound=BaseModel)


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


class ActorContextPayload(BaseModel):
    """Actor identity associated with a discussion lifecycle event."""

    user_id: str | None = None
    team_id: str | None = None


class DiscussionStartedPayload(BaseModel):
    """Structured payload for discussion start events."""

    question: str
    persona_ids: list[str] = Field(
        default_factory=list,
        validation_alias=AliasChoices("persona_ids", "personas"),
    )
    root_node_id: str = "root"
    request_config_snapshot: dict[str, Any] = Field(default_factory=dict)
    runtime_config_snapshot: dict[str, Any] = Field(default_factory=dict)
    migration_metadata: dict[str, Any] = Field(default_factory=dict)
    actor_context: ActorContextPayload = Field(default_factory=ActorContextPayload)
    selected_model_id: str | None = None
    resolved_model_slug: str | None = Field(
        default=None,
        validation_alias=AliasChoices("resolved_model_slug", "model"),
    )
    discussion_locale: str | None = Field(
        default=None,
        validation_alias=AliasChoices("discussion_locale", "locale"),
    )


class BlueHatDecisionPayload(BaseModel):
    """Coordinator decision describing the next step for the node."""

    node_id: str = "root"
    round: int = 1
    action: str | None = None
    hat: HatColor | None = None
    reasoning: str = ""
    target_persona_ids: list[str] = Field(default_factory=list)
    sub_question: str | None = None


class RoundStartedPayload(BaseModel):
    """Round execution starting for a specific node/hat."""

    node_id: str = "root"
    round: int = 1
    hat: HatColor | None = None
    target_persona_ids: list[str] = Field(default_factory=list)
    blue_hat_reasoning: str = ""


class RoundCompletedPayload(BaseModel):
    """Round execution finished for a specific node/hat."""

    node_id: str = "root"
    round: int = 1
    hat: HatColor | None = None
    outputs_count: int = 0


class ValidationResultPayload(BaseModel):
    """Validation outcome for a panelist response."""

    node_id: str = "root"
    round: int = 1
    persona_id: str = ""
    hat: HatColor | None = None
    passed: bool = True
    violations: list[str] = Field(default_factory=list)
    retry_count: int = 0


class PanelistOutputPayload(BaseModel):
    """Structured panelist output emitted after a round response."""

    node_id: str = "root"
    round: int = 1
    persona_id: str = ""
    hat: HatColor | None = None
    content: str = ""
    raw_content: str = ""
    items: list[OutputItem] = Field(default_factory=list)
    token_usage: TokenUsage = Field(default_factory=TokenUsage)
    validation_passed: bool = True
    validation_violations: list[str] = Field(default_factory=list)
    retry_count: int = 0


class ForkCreatedPayload(BaseModel):
    """Child discussion node created from a fork decision."""

    parent_node_id: str = "root"
    node_id: str = ""
    question: str = ""
    depth: int = 1


class VerdictPayload(BaseModel):
    """Portable verdict content shared by multiple terminal events."""

    summary: str = ""
    confidence: str = ""
    key_facts: list[str] = Field(default_factory=list)
    key_risks: list[str] = Field(default_factory=list)
    key_values: list[str] = Field(default_factory=list)
    mitigations: list[str] = Field(default_factory=list)
    intuition_summary: str = ""
    blue_hat_ruling: str = ""
    next_actions: list[str] = Field(default_factory=list)
    partial: bool = False
    bibliography: str = ""


class SubConclusionPayload(BaseModel):
    """Sub-tree conclusion emitted after finishing a forked branch."""

    node_id: str = ""
    summary: str = ""
    verdict: VerdictPayload = Field(default_factory=VerdictPayload)


class ConclusionPayload(VerdictPayload):
    """Final or forced conclusion for the active discussion."""

    token_usage: TokenUsage = Field(default_factory=TokenUsage)
    force_reason: str | None = None
    duration_seconds: float | None = None


class DiscussionCancelledPayload(VerdictPayload):
    """Cancellation result with partial verdict payload."""

    reason: str = "用户取消"
    node_id: str | None = None
    token_usage: TokenUsage = Field(default_factory=TokenUsage)


class BudgetWarningPayload(BaseModel):
    """Budget warning threshold crossing."""

    used_pct: float = 0.0
    level: str = "warning"


class DegradationChangedPayload(BaseModel):
    """Budget degradation state transition."""

    old_level: str = ""
    new_level: str = ""
    used_pct: float = 0.0
    total_tokens: int = 0
    total_cost: float = 0.0


class ContextCompressedPayload(BaseModel):
    """Context compression completion event."""

    node_id: str = "root"
    target_token: int = 0
    tokens_used: int = 0
    ratio: float = 0.0


class ErrorPayload(BaseModel):
    """Error details emitted on discussion failures."""

    message: str = ""
    node_id: str | None = None
    round: int | None = None
    code: str | None = None
    details: dict[str, Any] = Field(default_factory=dict)


class Event(BaseModel):
    """A single event emitted by the engine."""

    model_config = ConfigDict(populate_by_name=True)

    type: EventType
    payload: Any = Field(
        default_factory=dict,
        validation_alias=AliasChoices("payload", "data"),
    )

    def payload_as(self, payload_type: type[PayloadT]) -> PayloadT | None:
        """Return the payload as a typed model when coercion is possible."""

        if isinstance(self.payload, payload_type):
            return self.payload

        raw_payload: dict[str, Any]
        if isinstance(self.payload, BaseModel):
            raw_payload = self.payload.model_dump(mode="json")
        elif isinstance(self.payload, dict):
            raw_payload = dict(self.payload)
        else:
            return None

        try:
            return payload_type.model_validate(raw_payload)
        except ValidationError:
            return None

    @property
    def data(self) -> dict[str, Any]:
        if isinstance(self.payload, BaseModel):
            return self.payload.model_dump(mode="json")
        if isinstance(self.payload, dict):
            return dict(self.payload)
        return {}
