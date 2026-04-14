"""LiteLLM-based unified LLM backend."""

from __future__ import annotations

from typing import Any, Literal

import litellm

from hexmind.models.llm import LLMResponse, TokenPricing, TokenUsage


class LiteLLMWrapper:
    """Unified LLM backend wrapping LiteLLM SDK.

    Provides: completion, token counting, context limits, and pricing
    for 100+ models via a single interface.
    """

    def __init__(self, model: str = "gpt-4o", api_key: str | None = None) -> None:
        self._model = model
        if api_key:
            litellm.api_key = api_key
        # Suppress litellm debug noise
        litellm.suppress_debug_info = True

    # ── Core completion ─────────────────────────────────────────────

    async def complete(
        self,
        system_prompt: str,
        user_prompt: str,
        *,
        temperature: float = 0.7,
        max_tokens: int = 2000,
        response_format: Literal["text", "json"] = "text",
    ) -> LLMResponse:
        kwargs: dict[str, Any] = {
            "model": self._model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        if response_format == "json":
            kwargs["response_format"] = {"type": "json_object"}

        resp = await litellm.acompletion(**kwargs)
        choice = resp.choices[0]
        usage = resp.usage

        return LLMResponse(
            content=choice.message.content or "",
            usage=TokenUsage(
                input_tokens=usage.prompt_tokens if usage else 0,
                output_tokens=usage.completion_tokens if usage else 0,
                total_tokens=usage.total_tokens if usage else 0,
            ),
            model=resp.model or self._model,
            finish_reason=choice.finish_reason or "stop",
        )

    # ── Token accounting ────────────────────────────────────────────

    def count_tokens(self, text: str) -> int:
        """Count tokens for a plain text string."""
        return litellm.token_counter(model=self._model, text=text)

    def count_messages_tokens(self, messages: list[dict[str, str]]) -> int:
        """Count tokens for a messages list (includes role/format overhead)."""
        return litellm.token_counter(model=self._model, messages=messages)

    # ── Model metadata ──────────────────────────────────────────────

    @property
    def context_limit(self) -> int:
        try:
            return litellm.get_max_tokens(self._model)  # type: ignore[return-value]
        except Exception:
            return 128_000  # safe default for modern models

    @property
    def model_name(self) -> str:
        return self._model

    @property
    def pricing(self) -> TokenPricing | None:
        info = litellm.model_cost.get(self._model)
        if info:
            return TokenPricing(
                input_per_million=info.get("input_cost_per_token", 0) * 1_000_000,
                output_per_million=info.get("output_cost_per_token", 0) * 1_000_000,
            )
        return None
