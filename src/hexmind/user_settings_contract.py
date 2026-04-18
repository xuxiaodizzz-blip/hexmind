"""Shared models and helpers for structured user settings."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field

USER_SETTINGS_NAMESPACE_KEYS = (
    "ui_preferences",
    "discussion_preferences",
    "feature_flags",
)

_LEGACY_UI_KEY_MAP = {
    "locale": "ui_locale",
    "ui_locale": "ui_locale",
    "theme": "theme_mode",
    "theme_mode": "theme_mode",
    "luminance_mode": "theme_mode",
}

_LEGACY_DISCUSSION_KEY_MAP = {
    "discussion_locale": "default_discussion_locale",
    "default_discussion_locale": "default_discussion_locale",
    "selected_model": "default_selected_model_id",
    "selected_model_id": "default_selected_model_id",
    "default_selected_model_id": "default_selected_model_id",
    "model": "default_selected_model_id",
    "analysis_depth": "default_analysis_depth",
    "default_analysis_depth": "default_analysis_depth",
    "execution_token_cap": "default_execution_token_cap",
    "default_execution_token_cap": "default_execution_token_cap",
    "token_budget": "default_execution_token_cap",
    "discussion_max_rounds": "default_discussion_max_rounds",
    "default_discussion_max_rounds": "default_discussion_max_rounds",
    "max_rounds": "default_discussion_max_rounds",
    "time_budget_seconds": "default_time_budget_seconds",
    "default_time_budget_seconds": "default_time_budget_seconds",
}


class UIPreferences(BaseModel):
    """Preferences that affect the product shell rather than discussion execution."""

    ui_locale: Literal["zh", "en"] = "zh"
    theme_mode: Literal["light", "dark", "system"] = "system"


class DiscussionPreferences(BaseModel):
    """User-level defaults for future discussion creation."""

    default_discussion_locale: Literal["zh", "en"] = "zh"
    default_selected_model_id: str | None = None
    default_analysis_depth: Literal["quick", "standard", "deep"] | None = None
    default_execution_token_cap: int | None = Field(
        default=None,
        ge=5_000,
        le=500_000,
    )
    default_discussion_max_rounds: int | None = Field(
        default=None,
        ge=1,
        le=20,
    )
    default_time_budget_seconds: int | None = Field(
        default=None,
        ge=60,
    )


class UserSettings(BaseModel):
    """Structured replacement for the legacy flat settings bag."""

    ui_preferences: UIPreferences = Field(default_factory=UIPreferences)
    discussion_preferences: DiscussionPreferences = Field(default_factory=DiscussionPreferences)
    feature_flags: dict[str, bool] = Field(default_factory=dict)


class UIPreferencesPatch(BaseModel):
    """Partial update payload for UI preferences."""

    ui_locale: Literal["zh", "en"] | None = None
    theme_mode: Literal["light", "dark", "system"] | None = None


class DiscussionPreferencesPatch(BaseModel):
    """Partial update payload for discussion defaults."""

    default_discussion_locale: Literal["zh", "en"] | None = None
    default_selected_model_id: str | None = None
    default_analysis_depth: Literal["quick", "standard", "deep"] | None = None
    default_execution_token_cap: int | None = Field(
        default=None,
        ge=5_000,
        le=500_000,
    )
    default_discussion_max_rounds: int | None = Field(
        default=None,
        ge=1,
        le=20,
    )
    default_time_budget_seconds: int | None = Field(
        default=None,
        ge=60,
    )


class UserSettingsUpdate(BaseModel):
    """Partial settings update payload."""

    ui_preferences: UIPreferencesPatch | None = None
    discussion_preferences: DiscussionPreferencesPatch | None = None
    feature_flags: dict[str, bool] | None = None


def normalize_user_settings(settings: dict[str, Any] | None) -> dict[str, Any]:
    """Normalize legacy and partial settings into explicit namespaces."""

    normalized = UserSettings().model_dump(mode="python")
    raw = dict(settings or {})

    if any(key in raw for key in USER_SETTINGS_NAMESPACE_KEYS):
        ui_raw = raw.get("ui_preferences")
        if isinstance(ui_raw, dict):
            normalized["ui_preferences"].update(ui_raw)

        discussion_raw = raw.get("discussion_preferences")
        if isinstance(discussion_raw, dict):
            normalized["discussion_preferences"].update(discussion_raw)

        flags_raw = raw.get("feature_flags")
        if isinstance(flags_raw, dict):
            normalized["feature_flags"].update(
                {key: value for key, value in flags_raw.items() if isinstance(value, bool)}
            )

        raw = {
            key: value
            for key, value in raw.items()
            if key not in USER_SETTINGS_NAMESPACE_KEYS
        }

    _apply_legacy_settings(normalized, raw)
    return UserSettings.model_validate(normalized).model_dump(mode="python")


def merge_user_settings(
    current: dict[str, Any] | None,
    patch: dict[str, Any] | None,
) -> dict[str, Any]:
    """Merge a patch into current settings while preserving namespace structure."""

    normalized = normalize_user_settings(current)
    raw_patch = dict(patch or {})

    ui_patch = raw_patch.get("ui_preferences")
    if isinstance(ui_patch, dict):
        normalized["ui_preferences"].update(ui_patch)

    discussion_patch = raw_patch.get("discussion_preferences")
    if isinstance(discussion_patch, dict):
        normalized["discussion_preferences"].update(discussion_patch)

    flags_patch = raw_patch.get("feature_flags")
    if isinstance(flags_patch, dict):
        normalized["feature_flags"].update(
            {key: value for key, value in flags_patch.items() if isinstance(value, bool)}
        )

    legacy_patch = {
        key: value
        for key, value in raw_patch.items()
        if key not in USER_SETTINGS_NAMESPACE_KEYS
    }
    _apply_legacy_settings(normalized, legacy_patch)
    return UserSettings.model_validate(normalized).model_dump(mode="python")


def _apply_legacy_settings(target: dict[str, Any], raw: dict[str, Any]) -> None:
    for key, value in raw.items():
        if key in _LEGACY_UI_KEY_MAP:
            target["ui_preferences"][_LEGACY_UI_KEY_MAP[key]] = value
            continue

        if key in _LEGACY_DISCUSSION_KEY_MAP:
            target["discussion_preferences"][_LEGACY_DISCUSSION_KEY_MAP[key]] = value
            continue

        if isinstance(value, bool):
            target["feature_flags"][key] = value
