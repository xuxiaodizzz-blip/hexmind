"""Persona loader — loads Persona definitions from YAML files."""

from __future__ import annotations

import os
import re
from pathlib import Path

import yaml

from hexmind.models.persona import Persona

_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent

# Only allow alphanumeric, hyphens, and underscores in persona IDs
_VALID_PERSONA_ID = re.compile(r"^[a-zA-Z0-9_-]+$")


def _default_personas_dir() -> Path:
    """Resolve the default personas directory, honoring env overrides."""
    configured = os.getenv("HEXMIND_PERSONAS_DIR")
    if configured:
        return Path(configured)
    return _PROJECT_ROOT / "personas"


class PersonaLoader:
    """Load Persona objects from YAML files on disk."""

    def __init__(self, base_dir: Path | str | None = None) -> None:
        self._base_dir = Path(base_dir) if base_dir else _default_personas_dir()

    def load(self, persona_id: str) -> Persona:
        """Load a single persona by ID. Searches all subdirectories."""
        if not _VALID_PERSONA_ID.match(persona_id):
            raise ValueError(
                f"Invalid persona_id '{persona_id}': "
                "only alphanumeric characters, hyphens, and underscores allowed"
            )
        for path in self._base_dir.rglob(f"{persona_id}.yaml"):
            return self._load_file(path)
        for path in self._base_dir.rglob(f"{persona_id}.yml"):
            return self._load_file(path)
        raise FileNotFoundError(
            f"Persona '{persona_id}' not found in {self._base_dir}"
        )

    def load_all(self) -> list[Persona]:
        """Load all persona YAML files from base_dir (recursive)."""
        personas: list[Persona] = []
        for path in sorted(self._base_dir.rglob("*.yaml")):
            # Skip raw/ directory (scraped prompts, not persona definitions)
            if "raw" in path.parts:
                continue
            try:
                personas.append(self._load_file(path))
            except Exception:
                continue
        for path in sorted(self._base_dir.rglob("*.yml")):
            if "raw" in path.parts:
                continue
            try:
                personas.append(self._load_file(path))
            except Exception:
                continue
        return personas

    def list_ids(self) -> list[str]:
        """Return all available persona IDs."""
        return [p.id for p in self.load_all()]

    @property
    def base_dir(self) -> Path:
        return self._base_dir

    def save(self, persona: Persona, overwrite: bool = False) -> Path:
        """Save a Persona to disk as YAML. Returns the file path."""
        target_dir = self._base_dir / persona.domain
        target_dir.mkdir(parents=True, exist_ok=True)
        filepath = target_dir / f"{persona.id}.yaml"
        if filepath.exists() and not overwrite:
            raise FileExistsError(f"Persona file already exists: {filepath}")
        filepath.write_text(
            yaml.dump(
                persona.model_dump(),
                allow_unicode=True,
                default_flow_style=False,
            ),
            encoding="utf-8",
        )
        return filepath

    @staticmethod
    def _load_file(path: Path) -> Persona:
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
        return Persona.model_validate(data)
