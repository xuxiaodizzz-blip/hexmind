"""Model catalog and alias resolution backed by environment variables."""

from __future__ import annotations

import os
from collections.abc import Iterable
from typing import Literal

from dotenv import load_dotenv
from pydantic import BaseModel


class ModelCapabilities(BaseModel):
    """Feature flags exposed to product and frontend layers."""

    vision: bool = False
    tools: bool = False
    reasoning: bool = False
    max_output_mode: Literal["standard", "high_quality"] = "standard"


class ModelOption(BaseModel):
    """A single product-visible model choice."""

    id: str
    label: str
    slug: str
    capabilities: ModelCapabilities


class ModelCatalog(BaseModel):
    """Runtime model whitelist plus alias resolution helpers."""

    default_model_id: str
    fallback_model_id: str | None = None
    models: list[ModelOption]

    def get(self, model_id: str) -> ModelOption:
        for model in self.models:
            if model.id == model_id:
                return model
        raise KeyError(model_id)

    def resolve(self, model_id: str | None = None) -> ModelOption:
        return self.get(model_id or self.default_model_id)

    def fallback_for(self, model_id: str) -> ModelOption:
        target_id = self.fallback_model_id or model_id
        return self.get(target_id)


_HIGH_QUALITY_CAPABILITIES = ModelCapabilities(
    vision=True,
    tools=True,
    reasoning=True,
    max_output_mode="high_quality",
)

_BUILTIN_MODELS: dict[str, tuple[str, ModelCapabilities]] = {
    "opus": ("OPUS4.6", _HIGH_QUALITY_CAPABILITIES),
    "gpt": ("GPT5.4", _HIGH_QUALITY_CAPABILITIES),
    "sonnet": ("SONNET4.6", _HIGH_QUALITY_CAPABILITIES),
}


def _load_env(env_file: str | None = None) -> None:
    if env_file:
        load_dotenv(env_file)
    else:
        load_dotenv()


def load_model_catalog(env_file: str | None = None) -> ModelCatalog:
    """Load model alias catalog from environment variables."""
    _load_env(env_file)

    raw_map = os.getenv("HEXMIND_MODEL_MAP", "").strip()
    if raw_map:
        return _load_alias_catalog(raw_map)
    return _load_legacy_catalog()


def _load_alias_catalog(raw_map: str) -> ModelCatalog:
    entries = list(_parse_model_map(raw_map))
    if not entries:
        raise ValueError("HEXMIND_MODEL_MAP must declare at least one model")

    default_model_id = os.getenv("HEXMIND_DEFAULT_MODEL_ALIAS", "").strip() or entries[0][0]
    fallback_model_id = os.getenv("HEXMIND_FALLBACK_MODEL_ALIAS", "").strip() or None
    allowed_ids = {alias for alias, _ in entries}

    if default_model_id not in allowed_ids:
        raise ValueError(
            f"HEXMIND_DEFAULT_MODEL_ALIAS '{default_model_id}' is not present in HEXMIND_MODEL_MAP"
        )
    if fallback_model_id and fallback_model_id not in allowed_ids:
        raise ValueError(
            f"HEXMIND_FALLBACK_MODEL_ALIAS '{fallback_model_id}' is not present in HEXMIND_MODEL_MAP"
        )

    return ModelCatalog(
        default_model_id=default_model_id,
        fallback_model_id=fallback_model_id,
        models=[_build_option(alias, slug) for alias, slug in entries],
    )


def _load_legacy_catalog() -> ModelCatalog:
    default_slug = _first_env("HEXMIND_DEFAULT_MODEL", "HEXMIND_MODEL", default="gpt-4o")
    fallback_slug = os.getenv("HEXMIND_FALLBACK_MODEL", "").strip() or None
    raw_available = os.getenv("HEXMIND_AVAILABLE_MODELS", "")

    ordered_slugs = list(_unique_preserving_order([default_slug, fallback_slug, *raw_available.split(",")]))
    models = [
        ModelOption(
            id=slug,
            label=slug,
            slug=slug,
            capabilities=ModelCapabilities(),
        )
        for slug in ordered_slugs
        if slug
    ]
    if not models:
        models = [ModelOption(id=default_slug, label=default_slug, slug=default_slug, capabilities=ModelCapabilities())]

    return ModelCatalog(
        default_model_id=default_slug,
        fallback_model_id=fallback_slug if fallback_slug else None,
        models=models,
    )


def _build_option(alias: str, slug: str) -> ModelOption:
    builtin = _BUILTIN_MODELS.get(alias)
    if builtin:
        label, capabilities = builtin
    else:
        label, capabilities = alias, ModelCapabilities()
    return ModelOption(id=alias, label=label, slug=slug, capabilities=capabilities)


def _parse_model_map(raw_map: str) -> Iterable[tuple[str, str]]:
    seen: set[str] = set()
    for raw_item in raw_map.split(","):
        item = raw_item.strip()
        if not item:
            continue
        if "=" not in item:
            raise ValueError(
                "Invalid HEXMIND_MODEL_MAP entry. Expected 'alias=provider/model', "
                f"got '{item}'"
            )
        alias, slug = (part.strip() for part in item.split("=", 1))
        if not alias or not slug:
            raise ValueError(
                "Invalid HEXMIND_MODEL_MAP entry. Alias and slug must both be non-empty, "
                f"got '{item}'"
            )
        if alias in seen:
            raise ValueError(f"Duplicate model alias '{alias}' in HEXMIND_MODEL_MAP")
        seen.add(alias)
        yield alias, slug


def _unique_preserving_order(values: Iterable[str | None]) -> Iterable[str]:
    seen: set[str] = set()
    for value in values:
        item = (value or "").strip()
        if not item or item in seen:
            continue
        seen.add(item)
        yield item


def _first_env(*names: str, default: str) -> str:
    for name in names:
        value = os.getenv(name)
        if value:
            return value
    return default
