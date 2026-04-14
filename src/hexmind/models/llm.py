"""LLM response and token accounting models."""

from __future__ import annotations

from pydantic import BaseModel


class TokenUsage(BaseModel):
    """Token counts for a single LLM call."""

    input_tokens: int = 0
    output_tokens: int = 0
    total_tokens: int = 0


class TokenPricing(BaseModel):
    """Price per million tokens."""

    input_per_million: float
    output_per_million: float


class LLMResponse(BaseModel):
    """Standardized response from any LLM backend."""

    content: str
    usage: TokenUsage
    model: str
    finish_reason: str = "stop"


class ContextCheckResult(BaseModel):
    """Result of checking whether a prompt fits within context limits."""

    fits: bool
    prompt_tokens: int
    context_limit: int
    headroom: int  # context_limit - prompt_tokens
    needs_compression: bool = False
