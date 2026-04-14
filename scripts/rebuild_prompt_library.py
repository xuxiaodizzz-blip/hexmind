"""Rebuild the normalized prompt library from existing personas and raw prompts."""

from __future__ import annotations

import json
from collections import Counter
from pathlib import Path

from hexmind.personas.loader import PersonaLoader
from hexmind.prompt_library.loader import PromptLibraryLoader
from hexmind.prompt_library.normalizer import (
    build_builtin_hat_assets,
    build_prompt_asset_from_persona,
    build_prompt_asset_from_raw,
)

ROOT = Path(__file__).resolve().parent.parent
PERSONAS_DIR = ROOT / "personas"
RAW_PROMPTS_PATH = PERSONAS_DIR / "raw" / "prompts_all.json"
LIBRARY_DIR = ROOT / "prompts" / "library"


def ensure_unique_id(base_id: str, seen_ids: set[str]) -> str:
    """Ensure prompt asset IDs stay unique during rebuild."""
    if base_id not in seen_ids:
        seen_ids.add(base_id)
        return base_id

    suffix = 2
    while f"{base_id}-{suffix}" in seen_ids:
        suffix += 1
    new_id = f"{base_id}-{suffix}"
    seen_ids.add(new_id)
    return new_id


def iter_persona_assets() -> list:
    """Normalize all discussion personas into prompt assets."""
    loader = PersonaLoader(PERSONAS_DIR)
    assets = []
    for path in sorted(PERSONAS_DIR.rglob("*.yaml")):
        if "raw" in path.parts:
            continue
        try:
            persona = loader._load_file(path)
        except Exception:
            continue
        assets.append(
            build_prompt_asset_from_persona(persona, source_path=str(path.relative_to(ROOT)))
        )
    return assets


def iter_raw_prompt_assets() -> list:
    """Normalize all raw Feishu prompt records into prompt assets."""
    if not RAW_PROMPTS_PATH.exists():
        return []
    items = json.loads(RAW_PROMPTS_PATH.read_text(encoding="utf-8"))
    assets = []
    for item in items:
        prompt = (item.get("content") or "").strip()
        if not prompt:
            continue
        assets.append(
            build_prompt_asset_from_raw(
                item,
                source="feishu",
                source_path=str(RAW_PROMPTS_PATH.relative_to(ROOT)),
            )
        )
    return assets


def main() -> None:
    prompt_loader = PromptLibraryLoader(LIBRARY_DIR)
    prompt_loader.clear()

    seen_ids: set[str] = set()
    saved_assets = []

    builtins = build_builtin_hat_assets(source_path="src/hexmind/models/hat.py")
    for asset in builtins + iter_persona_assets() + iter_raw_prompt_assets():
        asset.id = ensure_unique_id(asset.id, seen_ids)
        prompt_loader.save(asset, overwrite=True)
        saved_assets.append(asset)

    by_source = Counter(asset.source for asset in saved_assets)
    by_status = Counter(asset.status for asset in saved_assets)
    by_hat_context = Counter(asset.hat_context for asset in saved_assets)

    print(f"Prompt Library 已重建到: {LIBRARY_DIR}")
    print(f"   总数: {len(saved_assets)}")
    for source, count in sorted(by_source.items()):
        print(f"   来源 {source:10s}: {count}")
    for status, count in sorted(by_status.items()):
        print(f"   状态 {status:10s}: {count}")
    for hat_context, count in sorted(by_hat_context.items()):
        print(f"   帽子 {hat_context:10s}: {count}")


if __name__ == "__main__":
    main()
