"""API request/response schemas — Pydantic models only, no IO."""

from __future__ import annotations

from typing import Literal

from pydantic import AliasChoices, BaseModel, ConfigDict, EmailStr, Field

from hexmind.models.llm import TokenUsage
from hexmind.user_settings_contract import UserSettings as UserSettingsResponse
from hexmind.user_settings_contract import UserSettingsUpdate as UserSettingsUpdateRequest


# ── Discussion ─────────────────────────────────────────────


class DiscussionConfigOverride(BaseModel):
    """Optional overrides for discussion configuration."""

    model_config = ConfigDict(populate_by_name=True)

    selected_model: str | None = Field(
        default=None,
        validation_alias=AliasChoices("selected_model", "model"),
    )
    analysis_depth: Literal["quick", "standard", "deep"] | None = None
    execution_token_cap: int = Field(
        default=50_000,
        ge=5_000,
        le=500_000,
        validation_alias=AliasChoices("execution_token_cap", "token_budget"),
    )
    discussion_max_rounds: int | None = Field(
        default=None,
        ge=1,
        le=20,
        validation_alias=AliasChoices("discussion_max_rounds", "max_rounds"),
    )
    time_budget_seconds: int | None = Field(
        default=None,
        ge=60,
    )
    discussion_locale: Literal["zh", "en"] = Field(
        default="zh",
        validation_alias=AliasChoices("discussion_locale", "locale"),
    )


class CreateDiscussionRequest(BaseModel):
    """POST /api/discussions body."""

    question: str = Field(min_length=5, max_length=500)
    persona_ids: list[str] = Field(min_length=2, max_length=5)
    config: DiscussionConfigOverride | None = None


class CreateDiscussionResponse(BaseModel):
    """POST /api/discussions response."""

    discussion_id: str
    status: str


class DiscussionStatusResponse(BaseModel):
    """GET /api/discussions/:id response."""

    discussion_id: str
    question: str
    run_state: Literal["running", "completed"]
    completion_status: Literal["converged", "partial", "cancelled", "error"] | None = None
    termination_reason: str | None = None
    status: str
    personas: list[str]
    rounds_completed: int
    token_used: int
    execution_token_cap: int
    exploration_token_cap: int
    finalization_reserve_token_cap: int


# ── Intervention ───────────────────────────────────────────


class InterventionRequest(BaseModel):
    """POST /api/discussions/:id/intervene body."""

    type: Literal["info", "direction", "stop"]
    content: str = Field(max_length=500)


# ── Archive ────────────────────────────────────────────────


class ArchiveSummary(BaseModel):
    """Summary of a single archived discussion."""

    id: str
    question: str
    created_at: str
    status: str
    personas: list[str]
    verdict: str | None = None
    confidence: str | None = None


class ArchiveListResponse(BaseModel):
    """GET /api/archive response."""

    total: int
    items: list[ArchiveSummary]


# ── Persona ────────────────────────────────────────────────


class PersonaSummary(BaseModel):
    """Lightweight persona listing item."""

    id: str
    name: str
    domain: str
    description: str


class PersonaDetail(BaseModel):
    """Full persona detail."""

    id: str
    name: str
    domain: str
    description: str
    prompt: str = ""


class CreatePersonaRequest(BaseModel):
    """POST /api/personas body."""

    model_config = ConfigDict(populate_by_name=True)

    id: str = Field(pattern=r"^[a-z0-9-]+$")
    name: str
    domain: Literal["tech", "business", "medical", "general"]
    description: str
    prompt: str = Field(
        default="",
        validation_alias=AliasChoices("prompt", "system_prompt_suffix"),
    )


class PromptSummary(BaseModel):
    """Lightweight prompt library listing item."""

    id: str
    name: str
    position: str
    domain: str
    kind: str
    hat: str | None = None
    hat_context: str
    applicable_hats: list[str]
    status: str
    source: str
    description: str


class PromptDetail(PromptSummary):
    """Full prompt library item."""

    prompt: str
    prompt_mode: str
    tags: list[str]
    source_title: str = ""
    source_path: str = ""


# ── Settings ───────────────────────────────────────────────


class ModelCapabilitiesSummary(BaseModel):
    """Frontend-safe model capability flags."""

    vision: bool = False
    tools: bool = False
    reasoning: bool = False
    max_output_mode: Literal["standard", "high_quality"] = "standard"


class ModelOptionSummary(BaseModel):
    """Frontend-safe model option."""

    id: str
    label: str
    capabilities: ModelCapabilitiesSummary


class AnalysisDepthOptionSummary(BaseModel):
    """Frontend-safe summary for one analysis depth preset."""

    id: Literal["quick", "standard", "deep"]
    max_personas: int
    execution_token_cap: int
    exploration_token_cap: int
    finalization_reserve_token_cap: int
    discussion_max_rounds: int
    time_budget_seconds: int
    supports_fork: bool


class AppSettings(BaseModel):
    """GET/POST /api/settings."""

    default_model_id: str = "gpt"
    models: list[ModelOptionSummary] = Field(default_factory=list)
    default_analysis_depth: Literal["quick", "standard", "deep"] = "standard"
    analysis_depths: list[AnalysisDepthOptionSummary] = Field(default_factory=list)
    plan_max_personas: int = 5
    default_execution_token_cap: int = 50_000
    default_discussion_max_rounds: int = 12
    default_time_budget_seconds: int = 300
    default_discussion_locale: Literal["zh", "en"] = "zh"


class ChatMessage(BaseModel):
    """Single OpenAI-style chat message."""

    role: Literal["system", "user", "assistant"]
    content: str = Field(min_length=1)


class ChatRequest(BaseModel):
    """POST /api/chat body."""

    selected_model: str | None = None
    messages: list[ChatMessage] = Field(min_length=1)
    stream: bool = False


class ChatCompletionResponse(BaseModel):
    """POST /api/chat response."""

    selected_model: str
    resolved_model: str
    content: str
    usage: TokenUsage = Field(default_factory=TokenUsage)
    finish_reason: str = "stop"


# ── Auth (Phase 5) ────────────────────────────────────────


class RegisterRequest(BaseModel):
    """POST /api/auth/register body."""

    email: EmailStr
    display_name: str = Field(max_length=100)
    password: str = Field(min_length=8, max_length=128)


class LoginRequest(BaseModel):
    """POST /api/auth/login body."""

    email: EmailStr
    password: str


class AuthResponse(BaseModel):
    """Token response after login/register."""

    access_token: str
    token_type: str = "bearer"
    user_id: str
    display_name: str


class UserProfile(BaseModel):
    """GET /api/auth/me response."""

    id: str
    email: str
    display_name: str
    created_at: str


# ── Team (Phase 5) ────────────────────────────────────────


class CreateTeamRequest(BaseModel):
    """POST /api/teams body."""

    name: str = Field(min_length=1, max_length=100)


class TeamSummary(BaseModel):
    """Team info for listing."""

    id: str
    name: str
    role: str
    member_count: int


class AddMemberRequest(BaseModel):
    """POST /api/teams/:id/members body."""

    email: EmailStr
    role: str = Field(default="member", pattern=r"^(admin|member|viewer)$")


class TeamMemberInfo(BaseModel):
    """Team member info."""

    user_id: str
    email: str
    display_name: str
    role: str


# ── Analytics (Phase 5) ──────────────────────────────────


class AnalyticsSummaryResponse(BaseModel):
    """GET /api/analytics/summary response."""

    total_discussions: int
    total_tokens_used: int
    total_cost_usd: float
    confidence_distribution: dict[str, int]
    hat_distribution: dict[str, int]


class PersonaStatItem(BaseModel):
    """Single persona stat entry."""

    persona_id: str
    hat: str
    count: int


# ── Billing / Pricing ─────────────────────────────────────


class PlanModelInfo(BaseModel):
    """Model available within a pricing plan."""

    id: str
    label: str


class PlanFeature(BaseModel):
    """Single feature line item in a pricing plan."""

    text: str
    text_zh: str


class PricingPlanResponse(BaseModel):
    """GET /api/billing/plans item."""

    id: str
    name: str
    name_zh: str
    price_monthly: float
    price_yearly: float
    badge: str | None = None
    badge_zh: str | None = None
    description: str
    description_zh: str
    models: list[PlanModelInfo] = Field(default_factory=list)
    features: list[PlanFeature] = Field(default_factory=list)
    highlighted: bool = False


class BillingInfoResponse(BaseModel):
    """GET /api/billing/info — current user billing status."""

    current_plan: str = "free"
    discussions_used: int = 0
    discussions_limit: int | None = 5
    credits_remaining: int = 50
    credits_monthly: int = 50
    plan_execution_token_cap: int = 50_000

