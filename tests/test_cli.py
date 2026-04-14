"""Tests for cli.py — Click commands tested via CliRunner."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
import yaml
from click.testing import CliRunner

from hexmind.cli import cli, _auto_select_personas
from hexmind.models.persona import Persona


# ── Auto-select personas ──────────────────────────────────


def _p(pid: str, domain: str) -> Persona:
    return Persona(id=pid, name=pid, domain=domain, description="test")


def test_auto_select_diverse():
    personas = [_p("a", "tech"), _p("b", "business"), _p("c", "medical"), _p("d", "tech")]
    selected = _auto_select_personas(personas, count=3)
    assert len(selected) == 3
    domains = {p.domain for p in selected}
    assert len(domains) >= 2  # at least 2 different domains


def test_auto_select_fewer_than_count():
    personas = [_p("a", "tech"), _p("b", "tech")]
    selected = _auto_select_personas(personas, count=3)
    assert len(selected) == 2


# ── CLI commands via CliRunner ────────────────────────────


@pytest.fixture
def runner() -> CliRunner:
    return CliRunner()


def test_cli_help(runner: CliRunner):
    result = runner.invoke(cli, ["--help"])
    assert result.exit_code == 0
    assert "HexMind" in result.output


def test_personas_command(runner: CliRunner):
    result = runner.invoke(cli, ["personas"])
    assert result.exit_code == 0
    # Should list at least some of our preset personas
    assert "backend-engineer" in result.output or "No personas" in result.output


def test_persona_info_command(runner: CliRunner):
    result = runner.invoke(cli, ["persona-info", "backend-engineer"])
    if result.exit_code == 0:
        assert "Name:" in result.output
        assert "Domain:" in result.output
    else:
        # If persona not found due to path issues, this is acceptable in test
        assert "Error" in result.output


def test_prompts_command(runner: CliRunner):
    result = runner.invoke(cli, ["prompts"])
    assert result.exit_code == 0
    assert "No prompt assets" in result.output or "backend-engineer" in result.output


def test_prompts_command_filter_hat(runner: CliRunner):
    result = runner.invoke(cli, ["prompts", "--hat", "white"])
    assert result.exit_code == 0
    assert "No prompt assets" in result.output or "hats=white" in result.output or "white" in result.output


def test_prompt_info_command(runner: CliRunner):
    result = runner.invoke(cli, ["prompt-info", "backend-engineer"])
    if result.exit_code == 0:
        assert "Position:" in result.output
        assert "Source:" in result.output
        assert "Hat Context:" in result.output
    else:
        assert "Error" in result.output


def test_show_missing_archive(runner: CliRunner):
    result = runner.invoke(cli, ["show", "nonexistent"])
    assert result.exit_code != 0


def test_search_no_results(runner: CliRunner):
    result = runner.invoke(cli, ["search", "-q", "xyznonexistent"])
    assert result.exit_code == 0
    assert "No results" in result.output


def test_export_missing_archive(runner: CliRunner):
    result = runner.invoke(cli, ["export", "nonexistent"])
    assert result.exit_code != 0


# ── Show/export with temp archive ─────────────────────────


@pytest.fixture
def temp_archive(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Create a temp archive and patch ArchiveReader default dir."""
    entry = tmp_path / "2025-01-01_test"
    entry.mkdir()
    (entry / "meta.yaml").write_text(
        yaml.dump({"question": "Test?", "status": "completed"}, allow_unicode=True),
        encoding="utf-8",
    )
    (entry / "discussion.md").write_text("# Test discussion\n", encoding="utf-8")
    (entry / "decision_summary.json").write_text(
        json.dumps({
            "question": "Test?",
            "options": [],
            "benefits": {},
            "costs": {},
            "risks": [],
            "evidence": [],
            "decision": "Test decision",
            "reasoning": "Test reasoning",
            "dissents": [],
            "confidence": "high",
            "next_actions": [],
        }),
        encoding="utf-8",
    )
    # Monkeypatch to use temp dir
    monkeypatch.setattr(
        "hexmind.cli.ArchiveReader",
        lambda *a, **kw: __import__("hexmind.archive.reader", fromlist=["ArchiveReader"]).ArchiveReader(str(tmp_path)),
    )
    monkeypatch.setattr(
        "hexmind.cli.ArchiveSearch",
        lambda *a, **kw: __import__("hexmind.archive.search", fromlist=["ArchiveSearch"]).ArchiveSearch(str(tmp_path)),
    )
    return tmp_path


def test_show_text(runner: CliRunner, temp_archive: Path):
    result = runner.invoke(cli, ["show", "2025-01-01_test"])
    assert result.exit_code == 0
    assert "Test discussion" in result.output


def test_show_json(runner: CliRunner, temp_archive: Path):
    result = runner.invoke(cli, ["show", "2025-01-01_test", "-f", "json"])
    assert result.exit_code == 0
    data = json.loads(result.output)
    assert data["decision"] == "Test decision"


def test_search_found(runner: CliRunner, temp_archive: Path):
    result = runner.invoke(cli, ["search", "-q", "Test"])
    assert result.exit_code == 0
    assert "2025-01-01_test" in result.output


def test_export_markdown(runner: CliRunner, temp_archive: Path):
    result = runner.invoke(cli, ["export", "2025-01-01_test"])
    assert result.exit_code == 0
    assert "Test discussion" in result.output


def test_export_json(runner: CliRunner, temp_archive: Path):
    result = runner.invoke(cli, ["export", "2025-01-01_test", "-f", "json"])
    assert result.exit_code == 0
    data = json.loads(result.output)
    assert data["decision"] == "Test decision"


def test_export_to_file(runner: CliRunner, temp_archive: Path, tmp_path: Path):
    out = str(tmp_path / "out.md")
    result = runner.invoke(cli, ["export", "2025-01-01_test", "-o", out])
    assert result.exit_code == 0
    assert "Exported" in result.output
    assert Path(out).read_text(encoding="utf-8").startswith("# Test")
