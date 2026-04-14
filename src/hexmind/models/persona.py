"""Persona definitions: role, knowledge, and prompt settings."""

from __future__ import annotations

from typing import Literal

from pydantic import AliasChoices, BaseModel, ConfigDict, Field


class PersonaTemperature(BaseModel):
    """LLM temperature per hat color, reflecting thinking style."""

    white: float = 0.3
    red: float = 0.9
    black: float = 0.5
    yellow: float = 0.6
    green: float = 0.8


class PersonaKnowledgeConfig(BaseModel):
    """Per-source knowledge retrieval config for a persona."""

    source: str  # e.g. "semantic_scholar", "pubmed", "local_files"
    auto_query: bool = True  # auto-search during White Hat
    max_results: int = 5
    filters: dict = Field(default_factory=dict)  # passed as SourceFilters fields


class Persona(BaseModel):
    """A discussion panelist with domain expertise and prompt settings."""

    model_config = ConfigDict(populate_by_name=True, extra="ignore")

    id: str = Field(pattern=r"^[a-z0-9-]+$")
    name: str
    domain: Literal["tech", "business", "medical", "general"]
    description: str
    temperature: PersonaTemperature = Field(default_factory=PersonaTemperature)
    prompt: str = Field(
        default="",
        validation_alias=AliasChoices("prompt", "system_prompt_suffix"),
    )
    knowledge_sources: list[PersonaKnowledgeConfig] = Field(default_factory=list)

    @property
    def display_name(self) -> str:
        return f"{self.name} ({self.domain})"

    @property
    def hat_preferences(self) -> dict[str, dict]:
        """Backward-compatible shim: hats are orthogonal to roles."""
        return {}

    @property
    def system_prompt_suffix(self) -> str:
        """Backward-compatible alias for legacy callers."""
        return self.prompt
