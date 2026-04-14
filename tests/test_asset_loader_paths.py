"""Tests for env-configurable persona and prompt asset roots."""

from __future__ import annotations

import yaml

from hexmind.personas.loader import PersonaLoader
from hexmind.prompt_library.loader import PromptLibraryLoader


def test_persona_loader_uses_env_override(tmp_path, monkeypatch):
    base_dir = tmp_path / "personas"
    persona_path = base_dir / "tech" / "backend-engineer.yaml"
    persona_path.parent.mkdir(parents=True, exist_ok=True)
    persona_path.write_text(
        yaml.dump(
            {
                "id": "backend-engineer",
                "name": "Backend Engineer",
                "domain": "tech",
                "description": "Test persona",
                "prompt": "Focus on reliability.",
            },
            allow_unicode=True,
            sort_keys=False,
        ),
        encoding="utf-8",
    )

    monkeypatch.setenv("HEXMIND_PERSONAS_DIR", str(base_dir))

    loader = PersonaLoader()

    assert loader.base_dir == base_dir
    assert loader.load("backend-engineer").id == "backend-engineer"


def test_prompt_loader_uses_env_override(tmp_path, monkeypatch):
    base_dir = tmp_path / "prompts" / "library"
    prompt_path = base_dir / "Backend Engineer" / "backend-engineer.yaml"
    prompt_path.parent.mkdir(parents=True, exist_ok=True)
    prompt_path.write_text(
        yaml.dump(
            {
                "id": "backend-engineer",
                "name": "Backend Engineer",
                "position": "Backend Engineer",
                "domain": "tech",
                "description": "Test prompt",
                "prompt": "Focus on APIs.",
                "kind": "persona",
                "prompt_mode": "suffix",
                "hat_context": "orthogonal",
                "hat": None,
                "applicable_hats": ["white", "black"],
                "tags": ["backend-engineer"],
                "source": "test",
                "source_title": "Backend Engineer",
                "source_path": "personas/tech/backend-engineer.yaml",
                "status": "ready",
            },
            allow_unicode=True,
            sort_keys=False,
        ),
        encoding="utf-8",
    )

    monkeypatch.setenv("HEXMIND_PROMPTS_DIR", str(base_dir))

    loader = PromptLibraryLoader()

    assert loader.base_dir == base_dir
    assert loader.load("backend-engineer").id == "backend-engineer"
