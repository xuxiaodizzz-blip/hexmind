"""Tests for the public repository export helper."""

from __future__ import annotations

from pathlib import Path

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
    assert (output_dir / "docs" / "public" / "assets" / "hexmind-demo.gif").exists()
    assert (output_dir / "docs" / "public" / "assets" / "hexmind-social-preview.png").exists()
    assert (output_dir / "scripts" / "render_readme_demo_gif.py").exists()
    assert not (output_dir / "personas" / "raw").exists()
    assert not (output_dir / "web" / "node_modules").exists()
    assert not (output_dir / "web" / "dist").exists()
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
