"""Hat color definitions, constraints, and validation rules."""

from __future__ import annotations

from enum import Enum

from pydantic import BaseModel


class HatColor(str, Enum):
    WHITE = "white"
    RED = "red"
    BLACK = "black"
    YELLOW = "yellow"
    GREEN = "green"


class HatConstraint(BaseModel):
    """Validation rules for a specific hat color's output."""

    prohibited_patterns: list[str] = []
    required_format: str | None = None
    max_sentences: int | None = None
    references_required: str | None = None  # "white" | "black" | None


HAT_CONSTRAINTS: dict[HatColor, HatConstraint] = {
    HatColor.WHITE: HatConstraint(
        prohibited_patterns=[
            r"我觉得|我认为|可能|大概|也许|I think|probably|maybe",
        ],
        required_format=r"^W\d+:",
        max_sentences=None,
        references_required=None,
    ),
    HatColor.RED: HatConstraint(
        prohibited_patterns=[],
        required_format=r"^直觉[：:]",
        max_sentences=3,
        references_required=None,
    ),
    HatColor.BLACK: HatConstraint(
        prohibited_patterns=[],
        required_format=r"^B\d+:",
        max_sentences=None,
        references_required="white",
    ),
    HatColor.YELLOW: HatConstraint(
        prohibited_patterns=[],
        required_format=r"^Y\d+:",
        max_sentences=None,
        references_required="white",
    ),
    HatColor.GREEN: HatConstraint(
        prohibited_patterns=[],
        required_format=r"^G\d+:",
        max_sentences=None,
        references_required="black",
    ),
}
