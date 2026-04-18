"""Runtime settings routes exposed to the frontend."""

from __future__ import annotations

from fastapi import APIRouter, Request

from hexmind.api.schemas import (
    AnalysisDepthOptionSummary,
    AppSettings,
    ModelCapabilitiesSummary,
    ModelOptionSummary,
)
from hexmind.config import load_config, load_discussion_plan
from hexmind.discussion_profiles import build_depth_option_summaries
from hexmind.model_catalog import ModelCatalog, load_model_catalog

router = APIRouter(prefix="/api/settings", tags=["settings"])


@router.get("/", response_model=AppSettings)
async def get_settings(request: Request) -> AppSettings:
    """Expose frontend-safe runtime settings sourced from backend env."""
    config = getattr(request.app.state, "runtime_config", None) or load_config()
    discussion_plan = (
        getattr(request.app.state, "discussion_plan", None) or load_discussion_plan()
    )
    catalog: ModelCatalog = getattr(request.app.state, "model_catalog", None) or load_model_catalog()

    return AppSettings(
        default_model_id=catalog.default_model_id,
        models=[
            ModelOptionSummary(
                id=model.id,
                label=model.label,
                capabilities=ModelCapabilitiesSummary.model_validate(model.capabilities.model_dump()),
            )
            for model in catalog.models
        ],
        default_analysis_depth=config.analysis_depth,
        analysis_depths=[
            AnalysisDepthOptionSummary.model_validate(option.model_dump())
            for option in build_depth_option_summaries(discussion_plan)
        ],
        plan_max_personas=discussion_plan.max_personas,
        default_execution_token_cap=config.execution_token_cap,
        default_discussion_max_rounds=config.discussion_max_rounds,
        default_time_budget_seconds=int(config.time_budget_seconds),
        default_discussion_locale=config.discussion_locale,
    )
