"""Export a GitHub-ready open-source snapshot from the private workspace."""

from __future__ import annotations

import argparse
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_OUTPUT_DIR = ROOT / "exports" / "github-public"

ROOT_FILE_MAPPINGS: dict[str, str] = {
    "ATTRIBUTIONS.md": "ATTRIBUTIONS.md",
    "CONTRIBUTING.md": "CONTRIBUTING.md",
    "SECURITY.md": "SECURITY.md",
    ".env.example": ".env.example",
    ".gitignore": ".gitignore",
    "LICENSE": "LICENSE",
    "pyproject.toml": "pyproject.toml",
    "README.public.md": "README.md",
}

DIR_MAPPINGS: dict[str, str] = {
    ".github": ".github",
    "src": "src",
    "tests": "tests",
    "docs/public": "docs/public",
    "open_source_assets/personas": "personas",
    "open_source_assets/prompts": "prompts",
}

FILE_MAPPINGS: dict[str, str] = {
    "web/index.html": "web/index.html",
    "web/package.json": "web/package.json",
    "web/package-lock.json": "web/package-lock.json",
    "web/tsconfig.json": "web/tsconfig.json",
    "web/vite.config.ts": "web/vite.config.ts",
    "scripts/generate_persona.py": "scripts/generate_persona.py",
    "scripts/prepare_public_repo.py": "scripts/prepare_public_repo.py",
    "scripts/render_readme_demo_gif.py": "scripts/render_readme_demo_gif.py",
    "scripts/rebuild_prompt_library.py": "scripts/rebuild_prompt_library.py",
}

WEB_DIR_MAPPINGS: dict[str, str] = {
    "web/src": "web/src",
}

EXPORT_IGNORE = shutil.ignore_patterns(
    "__pycache__",
    "*.pyc",
    "*.pyo",
    ".pytest_cache",
    ".mypy_cache",
    ".ruff_cache",
    "node_modules",
    "dist",
    ".vite",
)


def _copy_file(relative_src: str, relative_dst: str, output_dir: Path) -> None:
    src = ROOT / relative_src
    dst = output_dir / relative_dst
    if not src.exists():
        raise FileNotFoundError(f"Required export file not found: {src}")
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dst)


def _copy_tree(relative_src: str, relative_dst: str, output_dir: Path) -> None:
    src = ROOT / relative_src
    dst = output_dir / relative_dst
    if not src.exists():
        raise FileNotFoundError(f"Required export directory not found: {src}")
    shutil.copytree(src, dst, dirs_exist_ok=True, ignore=EXPORT_IGNORE)


def _reset_output_dir(output_dir: Path) -> None:
    """Clear exported contents while preserving an existing Git repo."""
    output_dir.mkdir(parents=True, exist_ok=True)
    for path in output_dir.iterdir():
        if path.name == ".git":
            continue
        if path.is_dir():
            shutil.rmtree(path)
        else:
            path.unlink()


def export_public_repo(output_dir: Path = DEFAULT_OUTPUT_DIR, *, overwrite: bool = False) -> Path:
    """Create a clean public export from the current private workspace."""
    output_dir = Path(output_dir)
    if output_dir.exists():
        if not overwrite:
            raise FileExistsError(
                f"Output directory already exists: {output_dir}. "
                "Pass --overwrite to replace it."
            )
        _reset_output_dir(output_dir)
    else:
        output_dir.mkdir(parents=True, exist_ok=True)

    for src, dst in ROOT_FILE_MAPPINGS.items():
        _copy_file(src, dst, output_dir)
    for src, dst in DIR_MAPPINGS.items():
        _copy_tree(src, dst, output_dir)
    for src, dst in FILE_MAPPINGS.items():
        _copy_file(src, dst, output_dir)
    for src, dst in WEB_DIR_MAPPINGS.items():
        _copy_tree(src, dst, output_dir)

    return output_dir


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Export a GitHub-ready open-source snapshot from the private workspace."
    )
    parser.add_argument(
        "--output",
        default=str(DEFAULT_OUTPUT_DIR),
        help="Destination directory for the exported repository.",
    )
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Replace the output directory if it already exists.",
    )
    args = parser.parse_args()

    exported = export_public_repo(Path(args.output), overwrite=args.overwrite)
    print(f"Public repo exported to: {exported}")


if __name__ == "__main__":
    main()
