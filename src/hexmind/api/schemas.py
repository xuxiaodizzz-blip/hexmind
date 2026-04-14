"""API request/response schemas — Pydantic models only, no IO."""

from __future__ import annotations

from typing import Literal

from pydantic import AliasChoices, BaseModel, ConfigDict, EmailStr, Field


# ── Discussion ─────────────────────────────────────────────


class DiscussionConfigOverride(BaseModel):
    """Optional overrides for discussion configuration."""

    model: str = "gpt-4o"
    token_budget: int = Field(default=50_000, ge=5_000, le=500_000)
    locale: Literal["zh", "en"] = "zh"


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
    status: str
    personas: list[str]
    rounds_completed: int
    token_used: int
    token_budget: int


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


class AppSettings(BaseModel):
    """GET/POST /api/settings."""

    default_model: str = "gpt-4o"
    fallback_model: str = "gpt-4o-mini"
    token_budget: int = 50_000
    locale: Literal["zh", "en"] = "zh"


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

