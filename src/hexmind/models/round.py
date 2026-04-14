"""Discussion round models: output items, panelist outputs, and rounds."""

from __future__ import annotations

from pydantic import BaseModel

from hexmind.models.hat import HatColor
from hexmind.models.llm import TokenUsage


class OutputItem(BaseModel):
    """A single numbered output entry, e.g. 'W1: ...'."""

    id: str  # "W1", "B2", "G3"
    content: str
    references: list[str] = []  # ["W1", "W3"]


class PanelistOutput(BaseModel):
    """One persona's output for a single hat round."""

    persona_id: str
    hat: HatColor
    content: str
    items: list[OutputItem]
    raw_content: str
    token_usage: TokenUsage
    validation_passed: bool
    validation_violations: list[str] = []
    retry_count: int = 0


class Round(BaseModel):
    """A single discussion round: one hat color, multiple panelist outputs."""

    number: int
    hat: HatColor
    blue_hat_reasoning: str
    outputs: list[PanelistOutput]
    timestamp: float
