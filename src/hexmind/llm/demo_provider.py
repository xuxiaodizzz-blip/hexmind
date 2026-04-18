"""Zero-cost demo provider used for hosted preview without burning trial budget.

When `HEXMIND_DEMO_MODE=true`, both `LiteLLMWrapper` and `RequestyTransport`
short-circuit to canned responses instead of calling any provider. This lets
GitHub visitors and waitlist landing-page traffic see a real-feeling discussion
without spending a single cent.

Design:

* Output is deterministic per (persona role + hat keyword) so visitors see
  variety but you can support repeat traffic without surprises.
* Token usage is reported as zero — `record_spend` won't accumulate against
  the daily circuit-breaker budget.
* Streaming yields characters with small async delays to mimic real SSE feel.
"""

from __future__ import annotations

import asyncio
import hashlib
import os
import random
from collections.abc import AsyncIterator
from typing import Any

from hexmind.models.llm import LLMResponse, TokenUsage


def is_demo_mode() -> bool:
    return os.getenv("HEXMIND_DEMO_MODE", "").strip().lower() in {"1", "true", "yes", "on"}


# Canned snippet pool keyed by hat color. Each list has multiple variants.
_CANNED: dict[str, list[str]] = {
    "white": [
        "From the data I have access to, the historical conversion rates for similar launches sit between 1.8% and 3.5%. The key uncertainty is the lack of segmented behavioral data for the new audience cohort.",
        "Three measurable facts: (1) infrastructure cost will rise by ~22% under the proposed change; (2) the test cohort is 480 users — large enough for direction but not significance; (3) similar features at peer companies took 6–10 weeks to mature.",
    ],
    "red": [
        "My instinct says ship it. The team has been circling this for two cycles and momentum matters. There's also some excitement among early users — that energy is real, even if it's unmeasurable right now.",
        "Honestly I'm uneasy. Something about the rollout plan feels rushed. I can't fully justify it with data, but every previous time I've felt this way the launch under-delivered.",
    ],
    "black": [
        "The rollback story is incomplete. If the schema migration fails on a customer with a non-trivial dataset, we have no documented recovery path beyond restoring backups, which violates the 4-hour RPO commitment.",
        "Two compounding risks: (1) external dependency on the auth provider's beta API, which has no SLA; (2) the billing edge case for prorated refunds is still tracked as 'TODO' in the design doc. Either alone is a launch blocker.",
    ],
    "yellow": [
        "If this works, the upside compounds. Each additional persona unlocks a new vertical, so a successful rollout to 200 customers in Q2 plausibly opens 5x that pipeline by year-end.",
        "The optimistic case here is that we are first-to-market with a workflow no one else has packaged yet. Timing windows like this rarely repeat — even a rough launch beats a polished competitor in 3 months.",
    ],
    "green": [
        "Alternative framing: instead of a full launch, run a 2-week founder-led concierge version with 8 hand-picked customers. We learn 80% of what a launch would teach us at 5% of the operational risk.",
        "What if we invert the rollout? Start with the highest-trust enterprise account willing to sign an early-access agreement, then expand to self-serve only after we've stress-tested the ops loop.",
    ],
    "blue": [
        "Let me consolidate: the data hat surfaced a measurement gap, the black hat flagged two unresolved blockers, and the green hat offered a lower-risk staged rollout. The decision tree forks on whether we accept a 2-week delay to close those blockers or proceed under known risk.",
        "Synthesis: there is no consensus on shipping today, but there is consensus on the staged-rollout structure. Recommended next step is to convert the green-hat suggestion into a concrete 2-week scope and re-evaluate the black-hat blockers against that scope.",
    ],
}

_DEFAULT_POOL = _CANNED["blue"]


def _seed_for(prompt: str) -> int:
    return int.from_bytes(hashlib.sha1(prompt.encode("utf-8", "ignore")).digest()[:4], "big")


def _pick_pool(prompt: str) -> list[str]:
    p = prompt.lower()
    for hat, pool in _CANNED.items():
        if hat in p or f"{hat} hat" in p:
            return pool
    return _DEFAULT_POOL


def canned_completion(system_prompt: str, user_prompt: str) -> str:
    """Pick a deterministic-but-varied canned response."""
    rng = random.Random(_seed_for(system_prompt + "||" + user_prompt))
    pool = _pick_pool(system_prompt + " " + user_prompt)
    return rng.choice(pool)


def canned_completion_for_messages(messages: list[dict[str, str]]) -> str:
    system_parts = [m.get("content", "") for m in messages if m.get("role") == "system"]
    user_parts = [m.get("content", "") for m in messages if m.get("role") != "system"]
    return canned_completion(" ".join(system_parts), " ".join(user_parts))


def build_demo_response(content: str, model: str) -> LLMResponse:
    return LLMResponse(
        content=content,
        usage=TokenUsage(input_tokens=0, output_tokens=0, total_tokens=0),
        model=model,
        finish_reason="stop",
    )


async def stream_demo_response(content: str, model: str) -> AsyncIterator[dict[str, Any]]:
    """Mimic Requesty SSE event shape."""
    # Chunk into small bursts for a streaming feel.
    chunk_size = 16
    for i in range(0, len(content), chunk_size):
        await asyncio.sleep(0.04)
        yield {"event": "delta", "data": {"content": content[i : i + chunk_size]}}
    yield {"event": "done", "data": {"model": model, "finish_reason": "stop"}}
