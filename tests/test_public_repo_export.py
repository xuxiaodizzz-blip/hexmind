"""Tests for the public repository export helper."""

from __future__ import annotations

from pathlib import Path

import scripts.prepare_public_repo as public_repo
from scripts.prepare_public_repo import export_public_repo


def test_export_public_repo_creates_clean_snapshot(tmp_path):
    output_dir = tmp_path / "github-public"

    exported = export_public_repo(output_dir)

    assert exported == output_dir
    assert (output_dir / "README.md").exists()
    assert (output_dir / "LICENSE").exists()
    assert (output_dir / "ATTRIBUTIONS.md").exists()
    assert (output_dir / "CONTRIBUTING.md").exists()
    assert (output_dir / "SECURITY.md").exists()
    assert (output_dir / ".github" / "workflows" / "ci.yml").exists()
    assert (output_dir / "src" / "hexmind" / "cli.py").exists()
    assert (output_dir / "web" / "src" / "App.tsx").exists()
    assert (output_dir / "personas" / "tech" / "backend-engineer.yaml").exists()
    assert (output_dir / "prompts" / "library" / "帽子协议" / "hat-white.yaml").exists()
    assert (output_dir / "docs" / "public" / "open-source-boundary.md").exists()
    assert (output_dir / "scripts" / "render_readme_demo_gif.py").exists()
    # New: local web entry points and pre-built SPA must ship in the public bundle.
    assert (output_dir / "start-local.bat").exists()
    assert (output_dir / "run_local_web.py").exists()
    assert (output_dir / "requirements-runtime.txt").exists()
    assert (output_dir / "web" / "dist" / "index.html").exists()
    assert not (output_dir / "personas" / "raw").exists()
    assert not (output_dir / "web" / "node_modules").exists()
    assert not list(output_dir.rglob("__pycache__"))


def test_export_public_repo_requires_overwrite(tmp_path):
    output_dir = tmp_path / "github-public"
    output_dir.mkdir()
    (output_dir / "stale.txt").write_text("stale", encoding="utf-8")

    try:
        export_public_repo(output_dir)
    except FileExistsError:
        pass
    else:
        raise AssertionError("Expected export_public_repo to require overwrite when output exists.")

    exported = export_public_repo(output_dir, overwrite=True)

    assert exported == output_dir
    assert not (output_dir / "stale.txt").exists()
    assert (output_dir / "README.md").exists()


def test_export_public_repo_overwrite_preserves_git_directory(tmp_path):
    output_dir = tmp_path / "github-public"
    git_dir = output_dir / ".git"
    git_dir.mkdir(parents=True)
    head_file = git_dir / "HEAD"
    head_file.write_text("ref: refs/heads/main\n", encoding="utf-8")
    (output_dir / "stale.txt").write_text("stale", encoding="utf-8")

    exported = export_public_repo(output_dir, overwrite=True)

    assert exported == output_dir
    assert head_file.exists()
    assert not (output_dir / "stale.txt").exists()


def test_export_public_repo_supports_already_public_layout(tmp_path, monkeypatch):
    public_root = tmp_path / "public-root"
    output_dir = tmp_path / "exported"
    public_root.mkdir()

    (public_root / "README.md").write_text("# Public README\n", encoding="utf-8")
    (public_root / "ATTRIBUTIONS.md").write_text("attr\n", encoding="utf-8")
    (public_root / "CONTRIBUTING.md").write_text("contrib\n", encoding="utf-8")
    (public_root / "SECURITY.md").write_text("security\n", encoding="utf-8")
    (public_root / ".env.example").write_text("ENV=1\n", encoding="utf-8")
    (public_root / ".gitignore").write_text("dist/\n", encoding="utf-8")
    (public_root / "LICENSE").write_text("MIT\n", encoding="utf-8")
    (public_root / "pyproject.toml").write_text("[project]\nname='hexmind'\n", encoding="utf-8")

    for path in [
        public_root / ".github" / "workflows" / "ci.yml",
        public_root / "src" / "hexmind" / "cli.py",
        public_root / "tests" / "test_public_repo_export.py",
        public_root / "docs" / "public" / "open-source-boundary.md",
        public_root / "docs" / "public" / "assets" / "hexmind-demo.gif",
        public_root / "docs" / "public" / "assets" / "hexmind-social-preview.png",
        public_root / "personas" / "tech" / "backend-engineer.yaml",
        public_root / "prompts" / "library" / "帽子协议" / "hat-white.yaml",
        public_root / "web" / "index.html",
        public_root / "web" / "package.json",
        public_root / "web" / "package-lock.json",
        public_root / "web" / "tsconfig.json",
        public_root / "web" / "vite.config.ts",
        public_root / "web" / "src" / "App.tsx",
        public_root / "scripts" / "generate_persona.py",
        public_root / "scripts" / "prepare_public_repo.py",
        public_root / "scripts" / "render_readme_demo_gif.py",
        public_root / "scripts" / "rebuild_prompt_library.py",
        # New required files for the local web entry points and pre-built SPA.
        public_root / "start-local.bat",
        public_root / "run_local_web.py",
        public_root / "requirements-runtime.txt",
        public_root / "web" / "dist" / "index.html",
    ]:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("placeholder\n", encoding="utf-8")

    monkeypatch.setattr(public_repo, "ROOT", public_root)
    monkeypatch.setattr(public_repo, "DEFAULT_OUTPUT_DIR", public_root / "exports" / "github-public")

    exported = public_repo.export_public_repo(output_dir)

    assert exported == output_dir
    assert (output_dir / "README.md").exists()
    assert (output_dir / "personas" / "tech" / "backend-engineer.yaml").exists()
    assert (output_dir / "prompts" / "library" / "帽子协议" / "hat-white.yaml").exists()
