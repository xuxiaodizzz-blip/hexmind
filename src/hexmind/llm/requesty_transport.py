"""Requesty OpenAI-compatible transport helpers."""

from __future__ import annotations

import asyncio
import json
import logging
import os
from collections.abc import AsyncIterator
from typing import Any

import httpx

from hexmind.llm.demo_provider import (
    build_demo_response,
    canned_completion_for_messages,
    is_demo_mode,
    stream_demo_response,
)
from hexmind.models.llm import LLMResponse, TokenUsage

logger = logging.getLogger(__name__)

# Status codes that warrant an automatic retry (rate-limit / transient server errors)
_RETRYABLE_STATUS_CODES = frozenset({429, 502, 503, 504})


class RequestyTransportError(RuntimeError):
    """Raised when the Requesty gateway rejects a request."""

    def __init__(self, message: str, status_code: int = 500) -> None:
        super().__init__(message)
        self.status_code = status_code


class RequestyTransport:
    """Minimal OpenAI-compatible client for Requesty."""

    def __init__(
        self,
        *,
        api_key: str | None = None,
        api_base: str | None = None,
        timeout_seconds: float = 90.0,
        max_retries: int = 3,
        retry_base_delay: float = 1.0,
    ) -> None:
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        self.api_base = (api_base or os.getenv("OPENAI_API_BASE") or "").rstrip("/")
        self.timeout_seconds = timeout_seconds
        self._max_retries = max_retries
        self._retry_base_delay = retry_base_delay

        # Demo mode bypasses credential validation — no provider call is made.
        if is_demo_mode():
            return

        if not self.api_key:
            raise ValueError("OPENAI_API_KEY is required for Requesty transport")
        if not self.api_base:
            raise ValueError("OPENAI_API_BASE is required for Requesty transport")

    def build_request(
        self,
        *,
        model: str,
        messages: list[dict[str, str]],
        temperature: float | None = None,
        max_tokens: int | None = None,
        response_format: dict[str, str] | None = None,
        stream: bool = False,
    ) -> tuple[str, dict[str, str], dict[str, Any]]:
        payload: dict[str, Any] = {
            "model": model,
            "messages": messages,
            "stream": stream,
        }
        if temperature is not None:
            payload["temperature"] = temperature
        if max_tokens is not None:
            payload["max_tokens"] = max_tokens
        if response_format is not None:
            payload["response_format"] = response_format

        return (
            f"{self.api_base}/chat/completions",
            {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            },
            payload,
        )

    async def complete(
        self,
        *,
        model: str,
        messages: list[dict[str, str]],
        temperature: float | None = None,
        max_tokens: int | None = None,
        response_format: dict[str, str] | None = None,
    ) -> LLMResponse:
        if is_demo_mode():
            return build_demo_response(
                canned_completion_for_messages(messages),
                model,
            )
        url, headers, payload = self.build_request(
            model=model,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
            response_format=response_format,
            stream=False,
        )
        response_json = await self._post_json(url, headers=headers, payload=payload)
        return self._parse_completion_response(response_json, model)

    async def stream_completion(
        self,
        *,
        model: str,
        messages: list[dict[str, str]],
        temperature: float | None = None,
        max_tokens: int | None = None,
        response_format: dict[str, str] | None = None,
    ) -> AsyncIterator[dict[str, Any]]:
        if is_demo_mode():
            content = canned_completion_for_messages(messages)
            async for event in stream_demo_response(content, model):
                yield event
            return
        done_emitted = False
        url, headers, payload = self.build_request(
            model=model,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
            response_format=response_format,
            stream=True,
        )
        async for line in self._stream_lines(url, headers=headers, payload=payload):
            if not line or not line.startswith("data:"):
                continue
            data = line[5:].strip()
            if not data:
                continue
            if data == "[DONE]":
                if not done_emitted:
                    yield {"event": "done", "data": {"model": model}}
                break

            chunk = self._load_json(data)
            choices = chunk.get("choices", [])
            if not choices:
                continue

            choice = choices[0]
            delta = choice.get("delta", {})
            content = delta.get("content")
            if isinstance(content, str) and content:
                yield {"event": "delta", "data": {"content": content}}

            finish_reason = choice.get("finish_reason")
            if finish_reason:
                done_emitted = True
                yield {
                    "event": "done",
                    "data": {
                        "model": chunk.get("model", model),
                        "finish_reason": finish_reason,
                    },
                }

    async def _post_json(
        self, url: str, *, headers: dict[str, str], payload: dict[str, Any]
    ) -> dict[str, Any]:
        timeout = httpx.Timeout(self.timeout_seconds)
        for attempt in range(self._max_retries + 1):
            try:
                async with httpx.AsyncClient(timeout=timeout) as client:
                    response = await client.post(url, headers=headers, json=payload)
                if response.status_code not in _RETRYABLE_STATUS_CODES or attempt == self._max_retries:
                    return self._json_or_raise(response)
                # Retryable status — fall through to backoff
                delay = self._retry_base_delay * (2 ** attempt)
                logger.warning(
                    "Requesty %d on attempt %d/%d, retrying in %.1fs",
                    response.status_code, attempt + 1, self._max_retries + 1, delay,
                )
                await asyncio.sleep(delay)
            except httpx.TimeoutException as exc:
                last_exc = exc
                if attempt == self._max_retries:
                    raise RequestyTransportError(
                        f"Request timed out after {self._max_retries + 1} attempts"
                    ) from exc
                delay = self._retry_base_delay * (2 ** attempt)
                logger.warning("Timeout on attempt %d, retrying in %.1fs", attempt + 1, delay)
                await asyncio.sleep(delay)
        # Should not reach here, but just in case
        raise RequestyTransportError("Max retries exhausted")  # pragma: no cover

    async def _stream_lines(
        self, url: str, *, headers: dict[str, str], payload: dict[str, Any]
    ) -> AsyncIterator[str]:
        timeout = httpx.Timeout(connect=10.0, read=None, write=self.timeout_seconds, pool=None)
        for attempt in range(self._max_retries + 1):
            stream_started = False
            try:
                async with httpx.AsyncClient(timeout=timeout) as client:
                    async with client.stream("POST", url, headers=headers, json=payload) as response:
                        if response.status_code in _RETRYABLE_STATUS_CODES and attempt < self._max_retries:
                            delay = self._retry_base_delay * (2 ** attempt)
                            logger.warning(
                                "Requesty stream %d on attempt %d/%d, retrying in %.1fs",
                                response.status_code, attempt + 1, self._max_retries + 1, delay,
                            )
                            await asyncio.sleep(delay)
                            continue
                        self._raise_for_status(response)
                        async for line in response.aiter_lines():
                            stream_started = True
                            yield line
                return  # stream completed successfully
            except httpx.TransportError as exc:
                if stream_started:
                    raise RequestyTransportError(
                        "Stream interrupted after partial output; automatic retry is disabled "
                        "once data has been emitted"
                    ) from exc
                if attempt == self._max_retries:
                    raise RequestyTransportError(
                        f"Stream failed after {self._max_retries + 1} attempts"
                    ) from exc
                delay = self._retry_base_delay * (2 ** attempt)
                logger.warning(
                    "Stream transport error on attempt %d, retrying in %.1fs",
                    attempt + 1,
                    delay,
                )
                await asyncio.sleep(delay)

        raise RequestyTransportError("Max stream retries exhausted")  # pragma: no cover

    def _json_or_raise(self, response: httpx.Response) -> dict[str, Any]:
        self._raise_for_status(response)
        return self._load_json(response.text)

    def _raise_for_status(self, response: httpx.Response) -> None:
        if response.status_code < 400:
            return
        message = self._extract_error_message(response)
        raise RequestyTransportError(message, status_code=response.status_code)

    def _extract_error_message(self, response: httpx.Response) -> str:
        try:
            payload = response.json()
        except Exception:
            return response.text or response.reason_phrase

        error = payload.get("error")
        if isinstance(error, dict):
            return str(error.get("message") or error)
        if isinstance(error, str):
            return error
        return str(payload.get("detail") or payload)

    def _load_json(self, value: str) -> dict[str, Any]:
        try:
            return json.loads(value)
        except json.JSONDecodeError as exc:
            raise RequestyTransportError(f"Invalid JSON from Requesty: {exc}") from exc

    def _parse_completion_response(
        self, payload: dict[str, Any], requested_model: str
    ) -> LLMResponse:
        choices = payload.get("choices", [])
        choice = choices[0] if choices else {}
        message = choice.get("message", {})
        usage = payload.get("usage", {})
        content = self._coerce_content(message.get("content"))

        return LLMResponse(
            content=content,
            usage=TokenUsage(
                input_tokens=int(usage.get("prompt_tokens", 0)),
                output_tokens=int(usage.get("completion_tokens", 0)),
                total_tokens=int(usage.get("total_tokens", 0)),
            ),
            model=str(payload.get("model") or requested_model),
            finish_reason=str(choice.get("finish_reason") or "stop"),
        )

    def _coerce_content(self, content: Any) -> str:
        if isinstance(content, str):
            return content
        if isinstance(content, list):
            parts: list[str] = []
            for item in content:
                if isinstance(item, str):
                    parts.append(item)
                elif isinstance(item, dict):
                    text = item.get("text")
                    if isinstance(text, str):
                        parts.append(text)
            return "".join(parts)
        return ""
