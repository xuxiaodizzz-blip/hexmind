"""Tests for config.py — environment variable loading."""

from __future__ import annotations

import os
from pathlib import Path

import pytest

from hexmind.config import load_config


def test_load_config_defaults():
    config = load_config()
    assert config.max_rounds == 12
    assert config.default_model == "gpt-4o"
    assert config.locale == "zh"
    assert config.token_budget == 50_000


def test_load_config_from_env(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("HEXMIND_MAX_ROUNDS", "6")
    monkeypatch.setenv("HEXMIND_MODEL", "claude-3-haiku")
    monkeypatch.setenv("HEXMIND_TOKEN_BUDGET", "100000")
    monkeypatch.setenv("HEXMIND_LOCALE", "en")

    config = load_config()
    assert config.max_rounds == 6
    assert config.default_model == "claude-3-haiku"
    assert config.token_budget == 100_000
    assert config.locale == "en"


def test_load_config_from_env_file(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    env_file = tmp_path / ".env"
    env_file.write_text(
        "HEXMIND_MAX_ROUNDS=8\n"
        "HEXMIND_MODEL=gpt-4o-mini\n"
        "HEXMIND_ARCHIVE_DIR=/tmp/archive\n",
        encoding="utf-8",
    )
    # Clear any existing env vars
    monkeypatch.delenv("HEXMIND_MAX_ROUNDS", raising=False)
    monkeypatch.delenv("HEXMIND_MODEL", raising=False)
    monkeypatch.delenv("HEXMIND_ARCHIVE_DIR", raising=False)

    config = load_config(str(env_file))
    assert config.max_rounds == 8
    assert config.default_model == "gpt-4o-mini"
    assert config.archive_dir == "/tmp/archive"


def test_env_var_overrides_dotenv(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    """Explicit env vars take priority over .env file."""
    env_file = tmp_path / ".env"
    env_file.write_text("HEXMIND_MAX_ROUNDS=8\n", encoding="utf-8")
    monkeypatch.setenv("HEXMIND_MAX_ROUNDS", "20")

    config = load_config(str(env_file))
    assert config.max_rounds == 20


def test_load_config_all_fields(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("HEXMIND_CONVERGENCE_THRESHOLD", "0.9")
    monkeypatch.setenv("HEXMIND_CONVERGENCE_CONSECUTIVE", "3")
    monkeypatch.setenv("HEXMIND_MAX_TREE_DEPTH", "5")
    monkeypatch.setenv("HEXMIND_MAX_TREE_WIDTH", "4")
    monkeypatch.setenv("HEXMIND_MAX_FORK_ROUNDS", "2")
    monkeypatch.setenv("HEXMIND_TOKEN_WARNING_PCT", "0.7")
    monkeypatch.setenv("HEXMIND_TIME_BUDGET", "600.0")
    monkeypatch.setenv("HEXMIND_FALLBACK_MODEL", "gpt-3.5-turbo")
    monkeypatch.setenv("HEXMIND_MAX_VALIDATION_RETRIES", "3")

    config = load_config()
    assert config.convergence_threshold == 0.9
    assert config.convergence_consecutive == 3
    assert config.max_tree_depth == 5
    assert config.max_tree_width == 4
    assert config.max_fork_rounds == 2
    assert config.token_warning_pct == 0.7
    assert config.time_budget_seconds == 600.0
    assert config.fallback_model == "gpt-3.5-turbo"
    assert config.max_validation_retries == 3
