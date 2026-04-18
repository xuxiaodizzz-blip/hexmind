"""Extract per-request user-supplied LLM credentials from HTTP headers.

This enables BYOK (Bring Your Own Key) flow: when a request carries
X-User-API-Key / X-User-API-Base headers, those override the server-side
defaults (env vars). Used so anonymous users can keep using the product
after their built-in trial quota is exhausted by supplying their own
OpenAI / Requesty key.

Headers are intentionally case-insensitive (FastAPI normalizes).
"""

from __future__ import annotations

from dataclasses import dataclass

from fastapi import Request


@dataclass(frozen=True)
class UserLLMCredentials:
    """User-supplied credentials parsed from request headers."""

    api_key: str | None = None
    api_base: str | None = None

    @property
    def is_present(self) -> bool:
        return bool(self.api_key)


def extract_user_credentials(request: Request) -> UserLLMCredentials:
    """Pull X-User-API-Key / X-User-API-Base headers from the request.

    Empty strings are treated as absent so the server falls back to env defaults.
    """
    raw_key = request.headers.get("x-user-api-key")
    raw_base = request.headers.get("x-user-api-base")
    api_key = raw_key.strip() if raw_key else None
    api_base = raw_base.strip().rstrip("/") if raw_base else None
    return UserLLMCredentials(
        api_key=api_key or None,
        api_base=api_base or None,
    )
