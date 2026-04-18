"""LiteLLM-based unified LLM backend."""

from __future__ import annotations

from typing import Any, Literal

import litellm

from hexmind.llm.demo_provider import (
    build_demo_response,
    canned_completion,
    is_demo_mode,
)
from hexmind.llm.requesty_transport import RequestyTransport
from hexmind.models.llm import LLMResponse, TokenPricing


class LiteLLMWrapper:
    """Unified LLM backend wrapping LiteLLM SDK.

    Provides: completion, token counting, context limits, and pricing
    for 100+ models via a single interface.
    """

    def __init__(
        self,
        model: str = "gpt-4o",
        api_key: str | None = None,
        api_base: str | None = None,
    ) -> None:
        self._model = model
        self._api_key = api_key
        self._api_base = api_base
        self._transport: RequestyTransport | None = None
        litellm.api_key = api_key or litellm.api_key
        # Suppress litellm debug noise
        litellm.suppress_debug_info = True

    def _get_transport(self) -> RequestyTransport:
        if self._transport is None:
            self._transport = RequestyTransport(
                api_key=self._api_key,
                api_base=self._api_base,
            )
        return self._transport

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
        if is_demo_mode():
            return build_demo_response(
                canned_completion(system_prompt, user_prompt),
                self._model,
            )
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

        return await self._get_transport().complete(
            model=kwargs["model"],
            messages=kwargs["messages"],
            temperature=kwargs["temperature"],
            max_tokens=kwargs["max_tokens"],
            response_format=kwargs.get("response_format"),
        )

    # ── Token accounting ────────────────────────────────────────────

    def count_tokens(self, text: str) -> int:
        """Count tokens for a plain text string."""
        try:
            return litellm.token_counter(model=self._model, text=text)
        except Exception:
            return max(1, len(text) // 4)

    def count_messages_tokens(self, messages: list[dict[str, str]]) -> int:
        """Count tokens for a messages list (includes role/format overhead)."""
        try:
            return litellm.token_counter(model=self._model, messages=messages)
        except Exception:
            return sum(self.count_tokens(item.get("content", "")) for item in messages)

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
