"""Unified chat route backed by the Requesty transport."""

from __future__ import annotations

import json

from fastapi import APIRouter, Depends, HTTPException, Request
from sse_starlette.sse import EventSourceResponse

from hexmind.api.schemas import ChatCompletionResponse, ChatRequest
from hexmind.api.trial_gate import commit_trial_consumption, evaluate_trial_gate
from hexmind.api.user_credentials import extract_user_credentials
from hexmind.archive.database import get_session_factory
from hexmind.auth.dependencies import get_optional_user_safe
from hexmind.llm.requesty_transport import RequestyTransport, RequestyTransportError
from hexmind.model_catalog import ModelCatalog, load_model_catalog

router = APIRouter(prefix="/api/chat", tags=["chat"])


def _get_model_catalog(request: Request) -> ModelCatalog:
    catalog = getattr(request.app.state, "model_catalog", None)
    return catalog or load_model_catalog()


@router.post("/", response_model=ChatCompletionResponse)
async def chat(
    request: Request,
    body: ChatRequest,
    user=Depends(get_optional_user_safe),
):
    catalog = _get_model_catalog(request)
    selected_model_id = body.selected_model.strip() if body.selected_model and body.selected_model.strip() else None
    try:
        selected_model = catalog.resolve(selected_model_id)
    except KeyError:
        raise HTTPException(422, f"Unknown selected_model: {body.selected_model}")

    # Trial gate: anonymous user with no BYOK header must consume free quota.
    try:
        factory = get_session_factory()
    except RuntimeError:
        factory = None
    gate_session = None
    if factory is not None:
        gate_session = factory()
    try:
        decision = await evaluate_trial_gate(request, user, gate_session)
    except Exception:
        if gate_session is not None:
            await gate_session.close()
        raise

    creds = decision.credentials
    try:
        transport = RequestyTransport(
            api_key=creds.api_key,
            api_base=creds.api_base,
        )
    except ValueError as exc:
        if gate_session is not None:
            await gate_session.close()
        raise HTTPException(500, str(exc)) from exc
    messages = [item.model_dump() for item in body.messages]

    if body.stream:
        async def event_generator():
            try:
                async for event in transport.stream_completion(
                    model=selected_model.slug,
                    messages=messages,
                ):
                    data = {
                        "selected_model": selected_model.id,
                        "resolved_model": selected_model.slug,
                        **event["data"],
                    }
                    yield {"event": event["event"], "data": json.dumps(data, ensure_ascii=False)}
            except RequestyTransportError as exc:
                yield {
                    "event": "error",
                    "data": json.dumps({"detail": str(exc)}, ensure_ascii=False),
                }
            finally:
                try:
                    await commit_trial_consumption(decision, gate_session)
                finally:
                    if gate_session is not None:
                        await gate_session.close()

        return EventSourceResponse(event_generator())

    try:
        response = await transport.complete(
            model=selected_model.slug,
            messages=messages,
        )
    except RequestyTransportError as exc:
        if gate_session is not None:
            await gate_session.close()
        raise HTTPException(exc.status_code, str(exc)) from exc

    try:
        await commit_trial_consumption(decision, gate_session)
    finally:
        if gate_session is not None:
            await gate_session.close()

    return ChatCompletionResponse(
        selected_model=selected_model.id,
        resolved_model=selected_model.slug,
        content=response.content,
        usage=response.usage,
        finish_reason=response.finish_reason,
    )
