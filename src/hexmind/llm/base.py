"""LLMBackend Protocol — the contract between llm layer and engine layer."""

from __future__ import annotations

from typing import Literal, Protocol, runtime_checkable

from hexmind.models.llm import LLMResponse, TokenPricing


@runtime_checkable
class LLMBackend(Protocol):
    """Unified interface for any LLM provider."""

    async def complete(
        self,
        system_prompt: str,
        user_prompt: str,
        *,
        temperature: float = 0.7,
        max_tokens: int = 2000,
        response_format: Literal["text", "json"] = "text",
    ) -> LLMResponse: ...

    def count_tokens(self, text: str) -> int: ...

    def count_messages_tokens(self, messages: list[dict[str, str]]) -> int: ...

    @property
    def context_limit(self) -> int: ...

    @property
    def model_name(self) -> str: ...

    @property
    def pricing(self) -> TokenPricing | None: ...
