"""Prompt library asset model."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

from hexmind.models.hat import HatColor


class PromptAsset(BaseModel):
    """A reusable prompt asset stored in the prompt library."""

    id: str = Field(pattern=r"^[\w\-\u4e00-\u9fff]+$")
    name: str
    position: str
    domain: str = "general"
    description: str = ""
    prompt: str
    kind: Literal["persona", "template", "workflow", "system", "hat"] = "template"
    prompt_mode: Literal["full", "suffix"] = "full"
    hat_context: Literal["general", "orthogonal", "hat-specific"] = "general"
    hat: HatColor | None = None
    applicable_hats: list[HatColor] = []
    tags: list[str] = []
    source: str = ""
    source_title: str = ""
    source_path: str = ""
    status: Literal["ready", "needs-review"] = "ready"
