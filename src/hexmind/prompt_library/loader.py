"""Prompt library loader for normalized prompt assets."""

from __future__ import annotations

import os
from pathlib import Path

import yaml

from hexmind.models.prompt_asset import PromptAsset
from hexmind.prompt_library.normalizer import slugify_asset_name

_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent


def _default_prompts_dir() -> Path:
    """Resolve the default prompt library directory, honoring env overrides."""
    configured = os.getenv("HEXMIND_PROMPTS_DIR")
    if configured:
        return Path(configured)
    return _PROJECT_ROOT / "prompts" / "library"


class PromptLibraryLoader:
    """Load and persist normalized prompt assets on disk."""

    def __init__(self, base_dir: Path | str | None = None) -> None:
        self._base_dir = Path(base_dir) if base_dir else _default_prompts_dir()

    def load(self, prompt_id: str) -> PromptAsset:
        """Load a single prompt asset by ID."""
        for path in self._iter_asset_files():
            if path.stem == prompt_id:
                return self._load_file(path)
        raise FileNotFoundError(f"Prompt asset '{prompt_id}' not found in {self._base_dir}")

    def load_all(self) -> list[PromptAsset]:
        """Load all prompt assets from disk."""
        assets: list[PromptAsset] = []
        for path in self._iter_asset_files():
            try:
                assets.append(self._load_file(path))
            except Exception:
                continue
        return sorted(assets, key=lambda asset: (asset.position, asset.name, asset.id))

    def list_positions(self) -> list[str]:
        """Return all distinct positions in the prompt library."""
        positions = {asset.position for asset in self.load_all()}
        return sorted(positions)

    @property
    def base_dir(self) -> Path:
        return self._base_dir

    def save(self, asset: PromptAsset, overwrite: bool = False) -> Path:
        """Save a prompt asset grouped by its position."""
        target_dir = self._base_dir / slugify_asset_name(asset.position, "unclassified")
        target_dir.mkdir(parents=True, exist_ok=True)
        filepath = target_dir / f"{asset.id}.yaml"
        if filepath.exists() and not overwrite:
            raise FileExistsError(f"Prompt asset already exists: {filepath}")
        filepath.write_text(
            yaml.dump(
                asset.model_dump(mode="json"),
                allow_unicode=True,
                sort_keys=False,
                default_flow_style=False,
            ),
            encoding="utf-8",
        )
        return filepath

    def clear(self) -> None:
        """Delete all normalized prompt assets under the base dir."""
        if not self._base_dir.exists():
            return
        for path in sorted(self._base_dir.rglob("*"), reverse=True):
            if path.is_file():
                path.unlink()
            elif path.is_dir():
                path.rmdir()

    def _iter_asset_files(self):
        for pattern in ("*.yaml", "*.yml"):
            for path in sorted(self._base_dir.rglob(pattern)):
                yield path

    @staticmethod
    def _load_file(path: Path) -> PromptAsset:
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
        return PromptAsset.model_validate(data)
