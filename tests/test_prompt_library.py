"""Tests for the normalized prompt library."""

from __future__ import annotations

from hexmind.models.persona import Persona
from hexmind.models.prompt_asset import PromptAsset
from hexmind.prompt_library.loader import PromptLibraryLoader
from hexmind.prompt_library.normalizer import (
    build_builtin_hat_assets,
    build_prompt_asset_from_persona,
    build_prompt_asset_from_raw,
    extract_position,
)


def test_extract_position_prefers_role_line():
    prompt = """## Role
Senior Product Manager
## Task
Analyze user needs.
"""
    assert extract_position("Created: 2025-06-01", prompt) == "Senior Product Manager"


def test_build_prompt_asset_from_raw_sets_status_for_fragments():
    asset = build_prompt_asset_from_raw(
        {
            "title": "### Core Principles",
            "content": "Generate content around the user's input.",
            "category": "creative",
        }
    )
    assert asset.status == "needs-review"


def test_build_prompt_asset_from_raw_detects_hat_usage():
    asset = build_prompt_asset_from_raw(
        {
            "title": "Black Hat Risk Analysis Template",
            "content": "Black Hat: list the risks. B1: risk one. Must cite W facts.",
            "category": "business",
        }
    )
    assert asset.hat_context == "hat-specific"
    assert asset.hat is not None and asset.hat.value == "black"
    assert [hat.value for hat in asset.applicable_hats] == ["black"]


def test_build_prompt_asset_from_persona_keeps_hats_orthogonal():
    persona = Persona(
        id="pm",
        name="Product Manager",
        domain="business",
        description="Product analysis",
        prompt="Focus on PMF.",
    )
    asset = build_prompt_asset_from_persona(persona)

    assert asset.hat_context == "orthogonal"
    assert asset.hat is None
    assert {hat.value for hat in asset.applicable_hats} == {
        "white",
        "red",
        "black",
        "yellow",
        "green",
    }
    assert "white" not in asset.tags


def test_build_builtin_hat_assets_creates_five_independent_hat_prompts():
    assets = build_builtin_hat_assets(source_path="src/hexmind/models/hat.py")
    assert len(assets) == 5
    assert {asset.kind for asset in assets} == {"hat"}
    assert {asset.hat.value for asset in assets if asset.hat is not None} == {
        "white",
        "red",
        "black",
        "yellow",
        "green",
    }
    assert all(asset.position == "帽子协议" for asset in assets)


def test_prompt_library_loader_roundtrip(tmp_path):
    loader = PromptLibraryLoader(tmp_path)
    asset = PromptAsset(
        id="backend-engineer-template",
        name="Backend Engineer Template",
        position="Backend Engineer",
        domain="tech",
        description="Backend analysis template",
        prompt="Analyze from a backend engineering perspective.",
        kind="template",
        prompt_mode="full",
        tags=["backend-engineer"],
        source="test",
        source_title="Backend Engineer Template",
    )

    path = loader.save(asset)
    loaded = loader.load("backend-engineer-template")

    assert path.exists()
    assert loaded == asset
    assert loader.list_positions() == ["Backend Engineer"]
