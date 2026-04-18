"""Tests for config.py and model catalog environment loading."""

from __future__ import annotations

from pathlib import Path

import pytest

from hexmind.config import load_config
from hexmind.model_catalog import load_model_catalog


def _empty_env_file(tmp_path: Path) -> str:
    env_file = tmp_path / ".env"
    env_file.write_text("", encoding="utf-8")
    return str(env_file)


def _clear_model_env(monkeypatch: pytest.MonkeyPatch) -> None:
    for name in (
        "HEXMIND_MODEL_MAP",
        "HEXMIND_DEFAULT_MODEL_ALIAS",
        "HEXMIND_FALLBACK_MODEL_ALIAS",
        "HEXMIND_DEFAULT_MODEL",
        "HEXMIND_MODEL",
        "HEXMIND_FALLBACK_MODEL",
        "HEXMIND_AVAILABLE_MODELS",
        "HEXMIND_DEFAULT_ANALYSIS_DEPTH",
        "HEXMIND_MAX_PERSONAS",
        "HEXMIND_EXECUTION_TOKEN_CAP",
        "HEXMIND_TOKEN_BUDGET",
        "HEXMIND_MAX_ROUNDS",
        "HEXMIND_TIME_BUDGET",
        "HEXMIND_MAX_TREE_DEPTH",
        "HEXMIND_MAX_TREE_WIDTH",
        "HEXMIND_MAX_FORK_ROUNDS",
        "HEXMIND_CONVERGENCE_THRESHOLD",
        "HEXMIND_CONVERGENCE_CONSECUTIVE",
        "HEXMIND_TOKEN_WARNING_PCT",
        "HEXMIND_MAX_VALIDATION_RETRIES",
        "HEXMIND_DISCUSSION_LOCALE",
        "HEXMIND_LOCALE",
        "HEXMIND_ARCHIVE_DIR",
    ):
        monkeypatch.delenv(name, raising=False)


def test_load_config_defaults(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    _clear_model_env(monkeypatch)

    config = load_config(_empty_env_file(tmp_path))
    assert config.analysis_depth == "standard"
    assert config.plan_discussion_max_rounds == 12
    assert config.max_rounds == 9
    assert config.default_model == "gpt-4o"
    assert config.selected_model_alias == "gpt-4o"
    assert config.discussion_locale == "zh"
    assert config.token_budget == 35_000


def test_load_model_catalog_from_alias_map(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    _clear_model_env(monkeypatch)
    env_file = tmp_path / ".env"
    env_file.write_text(
        "HEXMIND_MODEL_MAP=opus=anthropic/claude-opus-4-6,gpt=openai/gpt-5.4,sonnet=anthropic/claude-sonnet-4-6\n"
        "HEXMIND_DEFAULT_MODEL_ALIAS=opus\n",
        encoding="utf-8",
    )

    catalog = load_model_catalog(str(env_file))

    assert catalog.default_model_id == "opus"
    assert [model.id for model in catalog.models] == ["opus", "gpt", "sonnet"]
    assert catalog.resolve().slug == "anthropic/claude-opus-4-6"
    assert catalog.get("gpt").slug == "openai/gpt-5.4"
    assert catalog.get("sonnet").slug == "anthropic/claude-sonnet-4-6"


def test_load_config_from_env_file(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    _clear_model_env(monkeypatch)
    env_file = tmp_path / ".env"
    env_file.write_text(
        "HEXMIND_MAX_ROUNDS=8\n"
        "HEXMIND_MODEL_MAP=opus=anthropic/claude-opus-4-6,gpt=openai/gpt-5.4,sonnet=anthropic/claude-sonnet-4-6\n"
        "HEXMIND_DEFAULT_MODEL_ALIAS=gpt\n"
        "HEXMIND_ARCHIVE_DIR=/tmp/archive\n",
        encoding="utf-8",
    )

    config = load_config(str(env_file))
    assert config.plan_discussion_max_rounds == 8
    assert config.max_rounds == 6
    assert config.default_model == "openai/gpt-5.4"
    assert config.selected_model_alias == "gpt"
    assert config.archive_dir == "/tmp/archive"


def test_env_var_overrides_dotenv(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    _clear_model_env(monkeypatch)
    env_file = tmp_path / ".env"
    env_file.write_text(
        "HEXMIND_MAX_ROUNDS=8\n"
        "HEXMIND_MODEL_MAP=opus=anthropic/claude-opus-4-6,gpt=openai/gpt-5.4,sonnet=anthropic/claude-sonnet-4-6\n"
        "HEXMIND_DEFAULT_MODEL_ALIAS=opus\n",
        encoding="utf-8",
    )
    monkeypatch.setenv("HEXMIND_MAX_ROUNDS", "20")

    config = load_config(str(env_file))
    assert config.plan_discussion_max_rounds == 20
    assert config.max_rounds == 15


def test_load_config_all_fields(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    _clear_model_env(monkeypatch)
    env_file = _empty_env_file(tmp_path)
    monkeypatch.setenv("HEXMIND_DEFAULT_MODEL", "anthropic/claude-opus-4-6")
    monkeypatch.setenv("HEXMIND_CONVERGENCE_THRESHOLD", "0.9")
    monkeypatch.setenv("HEXMIND_CONVERGENCE_CONSECUTIVE", "3")
    monkeypatch.setenv("HEXMIND_MAX_TREE_DEPTH", "5")
    monkeypatch.setenv("HEXMIND_MAX_TREE_WIDTH", "4")
    monkeypatch.setenv("HEXMIND_MAX_FORK_ROUNDS", "2")
    monkeypatch.setenv("HEXMIND_TOKEN_WARNING_PCT", "0.7")
    monkeypatch.setenv("HEXMIND_TIME_BUDGET", "600.0")
    monkeypatch.setenv("HEXMIND_FALLBACK_MODEL", "gpt-3.5-turbo")
    monkeypatch.setenv("HEXMIND_MAX_VALIDATION_RETRIES", "3")
    monkeypatch.setenv("HEXMIND_DISCUSSION_LOCALE", "en")

    config = load_config(env_file)
    assert config.convergence_threshold == 0.9
    assert config.convergence_consecutive == 3
    assert config.plan_max_tree_depth == 5
    assert config.plan_max_tree_width == 4
    assert config.max_tree_depth == 2
    assert config.max_tree_width == 2
    assert config.max_fork_rounds == 2
    assert config.token_warning_pct == 0.7
    assert config.plan_time_budget_seconds == 600.0
    assert config.time_budget_seconds == 450.0
    assert config.fallback_model == "gpt-3.5-turbo"
    assert config.max_validation_retries == 3
    assert config.discussion_locale == "en"


def test_load_config_supports_legacy_locale_env(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    _clear_model_env(monkeypatch)
    env_file = _empty_env_file(tmp_path)
    monkeypatch.setenv("HEXMIND_LOCALE", "en")
    monkeypatch.delenv("HEXMIND_DISCUSSION_LOCALE", raising=False)

    config = load_config(env_file)

    assert config.discussion_locale == "en"


def test_load_config_supports_legacy_model_env(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    _clear_model_env(monkeypatch)
    env_file = _empty_env_file(tmp_path)
    monkeypatch.setenv("HEXMIND_DEFAULT_MODEL", "")
    monkeypatch.setenv("HEXMIND_MODEL", "legacy/provider-model")

    config = load_config(env_file)
    assert config.default_model == "legacy/provider-model"
    assert config.selected_model_alias == "legacy/provider-model"


def test_load_config_defaults_fallback_to_selected_alias(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    _clear_model_env(monkeypatch)
    env_file = tmp_path / ".env"
    env_file.write_text(
        "HEXMIND_MODEL_MAP=opus=anthropic/claude-opus-4-6,gpt=openai/gpt-5.4,sonnet=anthropic/claude-sonnet-4-6\n"
        "HEXMIND_DEFAULT_MODEL_ALIAS=opus\n",
        encoding="utf-8",
    )

    config = load_config(str(env_file))
    assert config.default_model == "anthropic/claude-opus-4-6"
    assert config.fallback_model == "anthropic/claude-opus-4-6"
    assert config.fallback_model_alias == "opus"


def test_load_model_catalog_rejects_duplicate_aliases(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    _clear_model_env(monkeypatch)
    env_file = _empty_env_file(tmp_path)
    monkeypatch.setenv(
        "HEXMIND_MODEL_MAP",
        "opus=anthropic/claude-opus-4-6,opus=openai/gpt-5.4",
    )
    monkeypatch.setenv("HEXMIND_DEFAULT_MODEL_ALIAS", "opus")

    with pytest.raises(ValueError, match="Duplicate model alias"):
        load_model_catalog(env_file)


def test_load_model_catalog_rejects_unknown_default_alias(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    _clear_model_env(monkeypatch)
    env_file = _empty_env_file(tmp_path)
    monkeypatch.setenv("HEXMIND_MODEL_MAP", "opus=anthropic/claude-opus-4-6")
    monkeypatch.setenv("HEXMIND_DEFAULT_MODEL_ALIAS", "gpt")

    with pytest.raises(ValueError, match="HEXMIND_DEFAULT_MODEL_ALIAS"):
        load_model_catalog(env_file)
