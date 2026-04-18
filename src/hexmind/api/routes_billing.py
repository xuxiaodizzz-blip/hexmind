"""Billing & pricing routes — plan tiers, credits, and model access.

Credits system
--------------
Each plan includes a monthly credit allowance. Using a model in a
discussion deducts credits based on actual token consumption:

  credits_consumed = input_tokens × model_input_rate
                   + output_tokens × model_output_rate

Model credit rates (credits per 1K tokens):
  GPT-4o mini   →  in: 0.2,  out: 0.6
  GPT-4o        →  in: 0.5,  out: 1.5
  GPT-5.4 mini  →  in: 0.8,  out: 2.5
  GPT-5.4       →  in: 1.0,  out: 6.0
  Sonnet 4.6    →  in: 0.6,  out: 3.0
  Opus 4.6      →  in: 3.0,  out: 15.0

Example: a 3-expert discussion using GPT-5.4, ~4K input + ~2K output
  each → (4×1.0) + (2×6.0) = 16 credits × 3 experts ≈ 48 credits.

Plan credit allowances (monthly):
  Free  →   50 credits  (≈ 1 small GPT-4o discussion)
  Pro   → 2,000 credits (≈ 40 GPT-5.4 discussions)
  Max   → 8,000 credits (≈ 30 Opus 4.6 discussions or 160 GPT-5.4)

Unused credits do NOT roll over. Extra credits can be purchased
at $1 per 100 credits (future).
"""

from __future__ import annotations

from fastapi import APIRouter, Request

from hexmind.api.schemas import (
    BillingInfoResponse,
    PlanFeature,
    PlanModelInfo,
    PricingPlanResponse,
)

router = APIRouter(prefix="/api/billing", tags=["billing"])


# ── Credit rates per 1K tokens ───────────────────────────

MODEL_CREDIT_RATES: dict[str, dict[str, float]] = {
    "openai/gpt-4o-mini":         {"input": 0.2,  "output": 0.6},
    "openai/gpt-4o":              {"input": 0.5,  "output": 1.5},
    "openai/gpt-5.4-mini":        {"input": 0.8,  "output": 2.5},
    "openai/gpt-5.4":             {"input": 1.0,  "output": 6.0},
    "anthropic/claude-sonnet-4-6": {"input": 0.6, "output": 3.0},
    "anthropic/claude-opus-4-6":   {"input": 3.0, "output": 15.0},
}


# ── Plan definitions ──────────────────────────────────────

_PLANS: list[dict] = [
    {
        "id": "free",
        "name": "Free",
        "name_zh": "免费版",
        "price_monthly": 0,
        "price_yearly": 0,
        "badge": None,
        "badge_zh": None,
        "description": "Get started with AI expert panels using standard models.",
        "description_zh": "使用基础模型体验 AI 专家组讨论。",
        "credits_monthly": 50,
        "models": [
            {"id": "openai/gpt-4o", "label": "GPT-4o"},
            {"id": "openai/gpt-4o-mini", "label": "GPT-4o mini"},
        ],
        "features": [
            {"text": "5 discussions / month", "text_zh": "每月 5 次讨论"},
            {"text": "Up to 3 experts per panel", "text_zh": "每次最多 3 位专家"},
            {"text": "50 credits included", "text_zh": "含 50 积分"},
            {"text": "Community support", "text_zh": "社区支持"},
        ],
        "highlighted": False,
    },
    {
        "id": "pro",
        "name": "Pro",
        "name_zh": "专业版",
        "price_monthly": 29,
        "price_yearly": 290,
        "badge": "Most Popular",
        "badge_zh": "最受欢迎",
        "description": "Full access to GPT-5.4 with generous credits for serious decision-making.",
        "description_zh": "完整使用 GPT-5.4，充裕积分，满足专业决策需求。",
        "credits_monthly": 2000,
        "models": [
            {"id": "openai/gpt-5.4", "label": "GPT-5.4"},
            {"id": "openai/gpt-5.4-mini", "label": "GPT-5.4 mini"},
            {"id": "openai/gpt-4o", "label": "GPT-4o"},
            {"id": "openai/gpt-4o-mini", "label": "GPT-4o mini"},
        ],
        "features": [
            {"text": "Unlimited discussions", "text_zh": "无限次讨论"},
            {"text": "Up to 5 experts per panel", "text_zh": "每次最多 5 位专家"},
            {"text": "2,000 credits / month", "text_zh": "每月 2,000 积分"},
            {"text": "Priority support", "text_zh": "优先支持"},
            {"text": "Export to Markdown & JSON", "text_zh": "导出 Markdown 和 JSON"},
        ],
        "highlighted": True,
    },
    {
        "id": "max",
        "name": "Max",
        "name_zh": "旗舰版",
        "price_monthly": 99,
        "price_yearly": 990,
        "badge": "Best Models",
        "badge_zh": "顶级模型",
        "description": "Access Claude Opus 4.6 and Sonnet 4.6 — the most capable AI models available.",
        "description_zh": "使用 Claude Opus 4.6 和 Sonnet 4.6 —— 最强 AI 模型。",
        "credits_monthly": 8000,
        "models": [
            {"id": "anthropic/claude-opus-4-6", "label": "Claude Opus 4.6"},
            {"id": "anthropic/claude-sonnet-4-6", "label": "Claude Sonnet 4.6"},
            {"id": "openai/gpt-5.4", "label": "GPT-5.4"},
            {"id": "openai/gpt-5.4-mini", "label": "GPT-5.4 mini"},
            {"id": "openai/gpt-4o", "label": "GPT-4o"},
        ],
        "features": [
            {"text": "Unlimited discussions", "text_zh": "无限次讨论"},
            {"text": "Up to 5 experts per panel", "text_zh": "每次最多 5 位专家"},
            {"text": "8,000 credits / month", "text_zh": "每月 8,000 积分"},
            {"text": "Dedicated support", "text_zh": "专属支持"},
            {"text": "Export to Markdown & JSON", "text_zh": "导出 Markdown 和 JSON"},
            {"text": "Team collaboration (soon)", "text_zh": "团队协作（即将推出）"},
        ],
        "highlighted": False,
    },
]


@router.get("/plans", response_model=list[PricingPlanResponse])
async def get_plans(request: Request) -> list[PricingPlanResponse]:
    """Return all available pricing plans."""
    return [
        PricingPlanResponse(
            id=p["id"],
            name=p["name"],
            name_zh=p["name_zh"],
            price_monthly=p["price_monthly"],
            price_yearly=p["price_yearly"],
            badge=p["badge"],
            badge_zh=p["badge_zh"],
            description=p["description"],
            description_zh=p["description_zh"],
            models=[PlanModelInfo(**m) for m in p["models"]],
            features=[PlanFeature(**f) for f in p["features"]],
            highlighted=p["highlighted"],
        )
        for p in _PLANS
    ]


@router.get("/info", response_model=BillingInfoResponse)
async def get_billing_info(request: Request) -> BillingInfoResponse:
    """Return current user billing info (stub — returns free tier)."""
    return BillingInfoResponse(
        current_plan="free",
        discussions_used=0,
        discussions_limit=5,
        credits_remaining=50,
        credits_monthly=50,
        plan_execution_token_cap=50_000,
    )


# ── Credit calculation helper ─────────────────────────────


def calculate_credits(model_slug: str, input_tokens: int, output_tokens: int) -> float:
    """Calculate credits consumed for a given model and token counts.

    Returns fractional credits. Callers should round as needed.
    Falls back to GPT-4o rates for unknown models.
    """
    rates = MODEL_CREDIT_RATES.get(model_slug)
    if rates is None:
        # Fall back to GPT-4o rates for unknown models
        rates = MODEL_CREDIT_RATES.get("openai/gpt-4o", {"input": 0.5, "output": 1.5})
    return (input_tokens / 1000) * rates["input"] + (output_tokens / 1000) * rates["output"]
