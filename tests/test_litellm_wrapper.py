"""Tests for Requesty-backed LLM transport and wrapper behavior."""

from __future__ import annotations

import httpx

import pytest

import hexmind.llm.requesty_transport as requesty_transport_module
from hexmind.llm.litellm_wrapper import LiteLLMWrapper
from hexmind.llm.requesty_transport import RequestyTransport, RequestyTransportError
from hexmind.models.llm import LLMResponse, TokenUsage


def test_requesty_transport_builds_openai_compatible_request(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "shared-key")
    monkeypatch.setenv("OPENAI_API_BASE", "https://router.example/v1")

    transport = RequestyTransport()
    url, headers, payload = transport.build_request(
        model="anthropic/claude-opus-4-6",
        messages=[{"role": "user", "content": "Hello"}],
        stream=False,
    )

    assert url == "https://router.example/v1/chat/completions"
    assert headers["Authorization"] == "Bearer shared-key"
    assert payload["model"] == "anthropic/claude-opus-4-6"
    assert payload["messages"] == [{"role": "user", "content": "Hello"}]
    assert payload["stream"] is False


@pytest.mark.asyncio
async def test_requesty_transport_parses_completion_response(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "shared-key")
    monkeypatch.setenv("OPENAI_API_BASE", "https://router.example/v1")

    async def fake_post_json(self, url, *, headers, payload):
        assert url == "https://router.example/v1/chat/completions"
        assert payload["model"] == "openai/gpt-5.4"
        return {
            "model": "openai/gpt-5.4",
            "choices": [
                {
                    "message": {"content": "Hello back"},
                    "finish_reason": "stop",
                }
            ],
            "usage": {
                "prompt_tokens": 12,
                "completion_tokens": 8,
                "total_tokens": 20,
            },
        }

    monkeypatch.setattr(RequestyTransport, "_post_json", fake_post_json)

    transport = RequestyTransport()
    response = await transport.complete(
        model="openai/gpt-5.4",
        messages=[{"role": "user", "content": "Hello"}],
    )

    assert response.content == "Hello back"
    assert response.model == "openai/gpt-5.4"
    assert response.usage.total_tokens == 20


@pytest.mark.asyncio
async def test_requesty_transport_streams_openai_chunks(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "shared-key")
    monkeypatch.setenv("OPENAI_API_BASE", "https://router.example/v1")

    async def fake_stream_lines(self, url, *, headers, payload):
        assert url == "https://router.example/v1/chat/completions"
        assert payload["model"] == "anthropic/claude-opus-4-6"
        yield 'data: {"model":"anthropic/claude-opus-4-6","choices":[{"delta":{"content":"Hi"},"finish_reason":null}]}'
        yield 'data: {"model":"anthropic/claude-opus-4-6","choices":[{"delta":{},"finish_reason":"stop"}]}'
        yield "data: [DONE]"

    monkeypatch.setattr(RequestyTransport, "_stream_lines", fake_stream_lines)

    transport = RequestyTransport()
    events = [
        event
        async for event in transport.stream_completion(
            model="anthropic/claude-opus-4-6",
            messages=[{"role": "user", "content": "Hello"}],
        )
    ]

    assert events[0] == {"event": "delta", "data": {"content": "Hi"}}
    assert events[1]["event"] == "done"
    assert events[1]["data"]["finish_reason"] == "stop"
    assert len(events) == 2


@pytest.mark.asyncio
async def test_requesty_transport_does_not_retry_after_partial_stream_output(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "shared-key")
    monkeypatch.setenv("OPENAI_API_BASE", "https://router.example/v1")

    calls: list[str] = []

    class FakeStreamResponse:
        def __init__(self, lines):
            self.status_code = 200
            self._lines = lines

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return False

        async def aiter_lines(self):
            for item in self._lines:
                if isinstance(item, Exception):
                    raise item
                yield item

    class FakeAsyncClient:
        def __init__(self, *args, **kwargs):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return False

        def stream(self, method, url, *, headers=None, json=None):
            calls.append(url)
            return FakeStreamResponse([
                'data: {"model":"anthropic/claude-opus-4-6","choices":[{"delta":{"content":"Hi"},"finish_reason":null}]}',
                httpx.ReadTimeout("stream interrupted"),
            ])

    monkeypatch.setattr(requesty_transport_module.httpx, "AsyncClient", FakeAsyncClient)

    transport = RequestyTransport(max_retries=1, retry_base_delay=0.0)
    events: list[dict] = []

    with pytest.raises(RequestyTransportError, match="partial output"):
        async for event in transport.stream_completion(
            model="anthropic/claude-opus-4-6",
            messages=[{"role": "user", "content": "Hello"}],
        ):
            events.append(event)

    assert events == [{"event": "delta", "data": {"content": "Hi"}}]
    assert len(calls) == 1


@pytest.mark.asyncio
async def test_litellm_wrapper_delegates_completion_to_requesty(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "shared-key")
    monkeypatch.setenv("OPENAI_API_BASE", "https://router.example/v1")

    async def fake_complete(
        self,
        *,
        model,
        messages,
        temperature=None,
        max_tokens=None,
        response_format=None,
    ):
        assert model == "anthropic/claude-opus-4-6"
        assert messages[0]["role"] == "system"
        assert response_format == {"type": "json_object"}
        return LLMResponse(
            content='{"ok":true}',
            usage=TokenUsage(total_tokens=42),
            model=model,
            finish_reason="stop",
        )

    monkeypatch.setattr(RequestyTransport, "complete", fake_complete)

    wrapper = LiteLLMWrapper(model="anthropic/claude-opus-4-6")
    response = await wrapper.complete(
        system_prompt="You are helpful.",
        user_prompt="Return JSON.",
        response_format="json",
    )

    assert response.content == '{"ok":true}'
    assert response.usage.total_tokens == 42
