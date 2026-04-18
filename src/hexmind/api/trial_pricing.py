"""Real USD pricing for built-in trial spend tracking.

Separate from `MODEL_CREDIT_RATES` (which is a product-level "credit" abstraction
for paid plans). This table tracks actual provider cost (Requesty markup + raw
model price) used to drive the global daily-budget circuit breaker.

Prices are USD per 1M tokens, valid as of 2026-04. Update when provider pricing
changes. Unknown models fall back to GPT-4o (conservative-ish default).
"""

from __future__ import annotations

# USD per 1,000,000 tokens.
MODEL_USD_PER_MTOKEN: dict[str, dict[str, float]] = {
    "openai/gpt-4o-mini":          {"input": 0.15,  "output": 0.60},
    "openai/gpt-4o":               {"input": 2.50,  "output": 10.00},
    "openai/gpt-5.4-mini":         {"input": 0.80,  "output": 3.20},
    "openai/gpt-5.4":              {"input": 5.00,  "output": 20.00},
    "anthropic/claude-sonnet-4-6": {"input": 3.00,  "output": 15.00},
    "anthropic/claude-opus-4-6":   {"input": 15.00, "output": 75.00},
}

_FALLBACK_KEY = "openai/gpt-4o"


def usd_cents_for(model_slug: str, input_tokens: int, output_tokens: int) -> int:
    """Estimated cost in integer USD cents (rounded up) for a single completion.

    Rounding up is intentional: the daily circuit-breaker should err on the side
    of stopping early rather than overshooting the $3 budget.
    """
    rates = MODEL_USD_PER_MTOKEN.get(model_slug) or MODEL_USD_PER_MTOKEN[_FALLBACK_KEY]
    usd = (input_tokens / 1_000_000) * rates["input"] + (
        output_tokens / 1_000_000
    ) * rates["output"]
    cents = usd * 100
    # Round up to the nearest integer cent so partial cents are not undercounted.
    return max(0, int(cents) + (1 if cents - int(cents) > 0 else 0))
