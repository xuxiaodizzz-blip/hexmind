import type { AnalysisDepthOption, AppSettings, DiscussionPreferences } from './api';

const LOCAL_DISCUSSION_PREFERENCES_KEY = 'hexmind-discussion-preferences';

export interface EffectiveDiscussionDefaults {
  selectedModel: string;
  analysisDepth: 'quick' | 'standard' | 'deep';
  discussionLocale: 'zh' | 'en';
}

function resolveModelId(appSettings: AppSettings, candidate: string | null | undefined): string {
  if (candidate && appSettings.models.some((model) => model.id === candidate)) {
    return candidate;
  }
  return appSettings.default_model_id;
}

function resolveAnalysisDepthId(
  appSettings: AppSettings,
  candidate: string | null | undefined,
): 'quick' | 'standard' | 'deep' {
  if (
    (candidate === 'quick' || candidate === 'standard' || candidate === 'deep')
    && appSettings.analysis_depths.some((depth) => depth.id === candidate)
  ) {
    return candidate;
  }
  return appSettings.default_analysis_depth;
}

export function resolveDepthOption(
  appSettings: AppSettings,
  depthId: 'quick' | 'standard' | 'deep',
): AnalysisDepthOption {
  return (
    appSettings.analysis_depths.find((depth) => depth.id === depthId)
    ?? appSettings.analysis_depths[0]
  );
}

export function resolveDiscussionDefaults(
  appSettings: AppSettings,
  overrides?: Partial<DiscussionPreferences> | null,
): EffectiveDiscussionDefaults {
  return {
    selectedModel: resolveModelId(appSettings, overrides?.default_selected_model_id),
    analysisDepth: resolveAnalysisDepthId(appSettings, overrides?.default_analysis_depth),
    discussionLocale:
      overrides?.default_discussion_locale === 'en' || overrides?.default_discussion_locale === 'zh'
        ? overrides.default_discussion_locale
        : appSettings.default_discussion_locale,
  };
}

export function readLocalDiscussionPreferences(): Partial<DiscussionPreferences> {
  const raw = localStorage.getItem(LOCAL_DISCUSSION_PREFERENCES_KEY);
  if (!raw) {
    return {};
  }

  try {
    const parsed = JSON.parse(raw) as Record<string, unknown>;
    return {
      default_selected_model_id:
        typeof parsed.default_selected_model_id === 'string'
          ? parsed.default_selected_model_id
          : null,
      default_analysis_depth:
        parsed.default_analysis_depth === 'quick'
        || parsed.default_analysis_depth === 'standard'
        || parsed.default_analysis_depth === 'deep'
          ? parsed.default_analysis_depth
          : null,
      default_discussion_locale:
        parsed.default_discussion_locale === 'en' || parsed.default_discussion_locale === 'zh'
          ? parsed.default_discussion_locale
          : undefined,
    };
  } catch {
    return {};
  }
}

export function writeLocalDiscussionPreferences(
  defaults: EffectiveDiscussionDefaults,
): void {
  const payload: DiscussionPreferences = {
    default_selected_model_id: defaults.selectedModel,
    default_analysis_depth: defaults.analysisDepth,
    default_discussion_locale: defaults.discussionLocale,
    default_execution_token_cap: null,
    default_discussion_max_rounds: null,
    default_time_budget_seconds: null,
  };
  localStorage.setItem(LOCAL_DISCUSSION_PREFERENCES_KEY, JSON.stringify(payload));
}
