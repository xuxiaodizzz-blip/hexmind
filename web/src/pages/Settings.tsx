import { useEffect, useRef, useState } from 'react';
import { motion } from 'motion/react';
import {
  Bot,
  Gauge,
  Languages,
  MessageSquare,
  Monitor,
  Moon,
  Palette,
  Save,
  Sparkles,
  Sun,
} from 'lucide-react';
import { Select } from '../components/ui';
import { useTheme } from '../hooks/useTheme';
import { useLanguage, type Locale } from '../hooks/useLanguage';
import * as api from '../lib/api';
import { AUTH_ENABLED } from '../lib/runtime';
import {
  resolveDiscussionDefaults,
  readLocalDiscussionPreferences,
  writeLocalDiscussionPreferences,
} from '../lib/discussionPreferences';
import { cn } from '../lib/utils';

type ThemeOption = 'light' | 'dark' | 'system';
type SaveState = 'idle' | 'saving' | 'saved' | 'error';
type AnalysisDepthId = 'quick' | 'standard' | 'deep';

function getDepthLabel(depth: AnalysisDepthId, locale: Locale): string {
  if (depth === 'quick') {
    return locale === 'en' ? 'Quick' : '快速';
  }
  if (depth === 'deep') {
    return locale === 'en' ? 'Deep' : '深入';
  }
  return locale === 'en' ? 'Standard' : '标准';
}

export default function Settings() {
  const { theme, setTheme } = useTheme();
  const { locale, setLocale, t } = useLanguage();
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [saveState, setSaveState] = useState<SaveState>('idle');
  const [saveMessage, setSaveMessage] = useState('');
  const [availableModels, setAvailableModels] = useState<api.ModelOption[]>([]);
  const [availableDepths, setAvailableDepths] = useState<api.AnalysisDepthOption[]>([]);
  const [selectedModel, setSelectedModel] = useState('');
  const [analysisDepth, setAnalysisDepth] = useState<AnalysisDepthId>('standard');
  const [discussionLocale, setDiscussionLocale] = useState<'zh' | 'en'>('zh');
  const [interfaceLocale, setInterfaceLocale] = useState<Locale>(locale);
  const [themeMode, setThemeMode] = useState<ThemeOption>(theme);
  const setLocaleRef = useRef(setLocale);
  const setThemeRef = useRef(setTheme);

  const isAuthenticated = AUTH_ENABLED && Boolean(api.getToken());
  const isEnglish = locale === 'en';
  const selectedDepthOption = availableDepths.find((depth) => depth.id === analysisDepth)
    ?? availableDepths[0]
    ?? null;
  const selectedModelOption = availableModels.find((model) => model.id === selectedModel) ?? null;

  useEffect(() => {
    setLocaleRef.current = setLocale;
    setThemeRef.current = setTheme;
  }, [setLocale, setTheme]);

  useEffect(() => {
    let cancelled = false;
    const bootLocale = localStorage.getItem('hexmind-language') === 'en' ? 'en' : 'zh';
    const storedTheme = localStorage.getItem('hexmind-theme');
    const bootTheme: ThemeOption =
      storedTheme === 'light' || storedTheme === 'dark' || storedTheme === 'system'
        ? storedTheme
        : 'system';

    async function loadSettings() {
      setLoading(true);
      setError('');

      try {
        const runtimeSettings = await api.getSettings();
        const localPreferences = readLocalDiscussionPreferences();
        let userSettings: api.UserSettings | null = null;

        if (isAuthenticated) {
          try {
            userSettings = await api.getMySettings();
          } catch (err) {
            if (!cancelled) {
              setSaveMessage(
                err instanceof api.ApiError
                  ? err.message
                  : (
                    bootLocale === 'en'
                      ? 'Failed to load synced settings. Using local values for now.'
                      : '加载账号设置失败，当前先使用本地值。'
                  ),
              );
            }
          }
        }

        if (cancelled) {
          return;
        }

        const discussionDefaults = resolveDiscussionDefaults(
          runtimeSettings,
          userSettings?.discussion_preferences ?? localPreferences,
        );

        setAvailableModels(runtimeSettings.models);
        setAvailableDepths(runtimeSettings.analysis_depths);
        setSelectedModel(discussionDefaults.selectedModel);
        setAnalysisDepth(discussionDefaults.analysisDepth);
        setDiscussionLocale(discussionDefaults.discussionLocale);

        const nextInterfaceLocale = userSettings?.ui_preferences.ui_locale ?? bootLocale;
        const nextThemeMode = userSettings?.ui_preferences.theme_mode ?? bootTheme;
        setInterfaceLocale(nextInterfaceLocale);
        setThemeMode(nextThemeMode);
        setLocaleRef.current(nextInterfaceLocale);
        setThemeRef.current(nextThemeMode);
      } catch (err) {
        if (cancelled) {
          return;
        }
        setError(
          err instanceof api.ApiError
            ? err.message
            : (
              bootLocale === 'en'
                ? 'Failed to load settings from the server.'
                : '加载后端设置失败。'
            ),
        );
      } finally {
        if (!cancelled) {
          setLoading(false);
        }
      }
    }

    void loadSettings();
    return () => {
      cancelled = true;
    };
  }, [isAuthenticated]);

  const languageOptions: { value: Locale; label: string; description: string }[] = [
    {
      value: 'en',
      label: 'English',
      description: locale === 'en' ? 'Menus, buttons, and labels in English' : '界面按钮与文案显示为英文',
    },
    {
      value: 'zh',
      label: '中文',
      description: locale === 'en' ? 'Menus, buttons, and labels in Chinese' : '界面按钮与文案显示为中文',
    },
  ];

  const discussionLanguageOptions = [
    {
      value: 'zh',
      label: locale === 'en' ? 'Chinese' : '中文',
      description: locale === 'en' ? 'New discussions default to Chinese output' : '新讨论默认输出为中文',
    },
    {
      value: 'en',
      label: 'English',
      description: locale === 'en' ? 'New discussions default to English output' : '新讨论默认输出为英文',
    },
  ];

  const modelOptions = availableModels.map((model) => ({
    value: model.id,
    label: model.label,
    description: locale === 'en' ? 'Backend allowlisted model' : '后端白名单模型',
  }));

  const depthOptions = availableDepths.map((depth) => ({
    value: depth.id,
    label: getDepthLabel(depth.id, locale),
    description: locale === 'en'
      ? `${depth.max_personas} experts · ${depth.discussion_max_rounds} rounds · ${Math.round(depth.time_budget_seconds / 60)}m`
      : `${depth.max_personas} 位专家 · ${depth.discussion_max_rounds} 轮 · ${Math.round(depth.time_budget_seconds / 60)} 分钟`,
  }));

  const themeOptions: { value: ThemeOption; label: string; icon: typeof Sun }[] = [
    { value: 'light', label: t('settings.theme.light'), icon: Sun },
    { value: 'dark', label: t('settings.theme.dark'), icon: Moon },
    { value: 'system', label: t('settings.theme.system'), icon: Monitor },
  ];

  function markDirty() {
    if (saveState !== 'saving') {
      setSaveState('idle');
      setSaveMessage('');
    }
  }

  function handleLocaleChange(value: string) {
    const nextLocale = value as Locale;
    setInterfaceLocale(nextLocale);
    setLocale(nextLocale);
    markDirty();
  }

  function handleThemeChange(value: ThemeOption) {
    setThemeMode(value);
    setTheme(value);
    markDirty();
  }

  async function handleSave() {
    const effectiveDefaults = {
      selectedModel,
      analysisDepth,
      discussionLocale,
    };

    setSaveState('saving');
    setSaveMessage('');

    try {
      if (isAuthenticated) {
        await api.updateMySettings({
          ui_preferences: {
            ui_locale: interfaceLocale,
            theme_mode: themeMode,
          },
          discussion_preferences: {
            default_selected_model_id: effectiveDefaults.selectedModel,
            default_analysis_depth: effectiveDefaults.analysisDepth,
            default_discussion_locale: effectiveDefaults.discussionLocale,
            default_execution_token_cap: null,
            default_discussion_max_rounds: null,
            default_time_budget_seconds: null,
          },
        });
        setSaveMessage(locale === 'en' ? 'Settings synced to your account.' : '设置已同步到你的账号。');
      } else {
        writeLocalDiscussionPreferences(effectiveDefaults);
        setSaveMessage(
          locale === 'en'
            ? 'Discussion defaults saved in this browser.'
            : '讨论默认值已保存在当前浏览器。',
        );
      }

      setSaveState('saved');
    } catch (err) {
      setSaveState('error');
      setSaveMessage(
        err instanceof api.ApiError
          ? err.message
          : (locale === 'en' ? 'Failed to save settings.' : '保存设置失败。'),
      );
    }
  }

  return (
    <div className="z-10 w-full flex-1 overflow-y-auto no-scrollbar p-8 lg:p-12">
      <div className="mx-auto max-w-5xl">
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          className="mb-10 flex flex-col gap-4 lg:flex-row lg:items-end lg:justify-between"
        >
          <div>
            <p className="text-[10px] font-bold uppercase tracking-[0.2em] text-white/40">
              {locale === 'en' ? 'Structured Settings' : '结构化设置'}
            </p>
            <h1 className="mt-2 text-4xl font-bold tracking-tight text-white">
              {locale === 'en' ? 'Tune The Default Operating Mode' : '调整系统默认运行方式'}
            </h1>
            <p className="mt-3 max-w-2xl text-sm text-white/50">
              {isAuthenticated
                ? (
                  locale === 'en'
                    ? 'Discussion defaults will follow your account across devices.'
                    : '讨论默认值会跟随你的账号，在不同设备之间保持一致。'
                )
                : (
                  locale === 'en'
                    ? 'Theme and interface language already save locally. Discussion defaults can also be stored in this browser.'
                    : '主题与界面语言已本地保存，讨论默认值也可以保存在当前浏览器。'
                )}
            </p>
          </div>

          <button
            type="button"
            onClick={handleSave}
            disabled={loading || !selectedModel || saveState === 'saving'}
            className="inline-flex items-center justify-center gap-2 rounded-xl bg-[#00e5ff] px-5 py-3 font-bold text-black transition-colors hover:bg-[#00cce6] disabled:cursor-not-allowed disabled:opacity-40"
          >
            <Save className="h-4 w-4" />
            {saveState === 'saving'
              ? (locale === 'en' ? 'Saving...' : '保存中...')
              : (locale === 'en' ? 'Save Settings' : '保存设置')}
          </button>
        </motion.div>

        {(error || saveMessage) && (
          <div
            className={cn(
              'mb-8 rounded-2xl border px-5 py-4 text-sm',
              error || saveState === 'error'
                ? 'border-red-500/30 bg-red-500/10 text-red-300'
                : 'border-[#00e5ff]/20 bg-[#00e5ff]/8 text-[#b9f6ff]',
            )}
          >
            {error || saveMessage}
          </div>
        )}

        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          className="mb-12"
        >
          <div className="mb-6 flex items-center gap-4">
            <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-[#1a202c]">
              <MessageSquare className="h-5 w-5 text-[#c3f5ff]" />
            </div>
            <h2 className="text-2xl font-serif italic text-white">
              {t('settings.discussionDefaults')}
            </h2>
          </div>

          <div className="rounded-2xl border border-white/5 bg-[#151a23] p-8 shadow-lg">
            {loading ? (
              <p className="text-sm text-white/50">
                {locale === 'en' ? 'Loading runtime defaults...' : '正在加载运行时默认值...'}
              </p>
            ) : (
              <div className="space-y-6">
                <div className="grid grid-cols-1 gap-6 md:grid-cols-3">
                  <div className="rounded-2xl border border-white/5 bg-[#11161f] p-5">
                    <div className="mb-4 flex items-center gap-3">
                      <Bot className="h-4 w-4 text-[#c3f5ff]" />
                      <h3 className="text-[10px] font-bold uppercase tracking-[0.15em] text-white/50">
                        {locale === 'en' ? 'Default Model' : '默认模型'}
                      </h3>
                    </div>
                    <Select
                      options={modelOptions}
                      value={selectedModel}
                      onChange={(value) => {
                        setSelectedModel(value);
                        markDirty();
                      }}
                      placeholder={locale === 'en' ? 'Choose a model' : '选择模型'}
                    />
                  </div>

                  <div className="rounded-2xl border border-white/5 bg-[#11161f] p-5">
                    <div className="mb-4 flex items-center gap-3">
                      <Sparkles className="h-4 w-4 text-[#c3f5ff]" />
                      <h3 className="text-[10px] font-bold uppercase tracking-[0.15em] text-white/50">
                        {locale === 'en' ? 'Analysis Depth' : '分析深度'}
                      </h3>
                    </div>
                    <Select
                      options={depthOptions}
                      value={analysisDepth}
                      onChange={(value) => {
                        setAnalysisDepth(value as AnalysisDepthId);
                        markDirty();
                      }}
                    />
                  </div>

                  <div className="rounded-2xl border border-white/5 bg-[#11161f] p-5">
                    <div className="mb-4 flex items-center gap-3">
                      <Languages className="h-4 w-4 text-[#c3f5ff]" />
                      <h3 className="text-[10px] font-bold uppercase tracking-[0.15em] text-white/50">
                        {locale === 'en' ? 'Discussion Language' : '讨论语言'}
                      </h3>
                    </div>
                    <Select
                      options={discussionLanguageOptions}
                      value={discussionLocale}
                      onChange={(value) => {
                        setDiscussionLocale(value as 'zh' | 'en');
                        markDirty();
                      }}
                    />
                  </div>
                </div>

                <div className="rounded-2xl border border-white/5 bg-[#11161f] p-5">
                  <div className="mb-5 flex items-center gap-3">
                    <Gauge className="h-4 w-4 text-[#c3f5ff]" />
                    <div>
                      <h3 className="text-[10px] font-bold uppercase tracking-[0.15em] text-white/50">
                        {locale === 'en' ? 'Resolved Runtime Profile' : '当前运行档位'}
                      </h3>
                      <p className="mt-1 text-sm text-white/45">
                        {locale === 'en'
                          ? 'These values are derived from the selected depth preset and backend plan envelope.'
                          : '这些数值由分析深度预设与后端计划上限共同推导，不再手动调整。'}
                      </p>
                    </div>
                  </div>

                  <div className="grid grid-cols-2 gap-4 md:grid-cols-3 xl:grid-cols-6">
                    <div className="rounded-xl border border-white/5 bg-white/5 p-4">
                      <p className="text-[10px] uppercase tracking-[0.12em] text-white/40">
                        {locale === 'en' ? 'Model' : '模型'}
                      </p>
                      <p className="mt-2 text-sm font-bold text-white">
                        {selectedModelOption?.label ?? selectedModel}
                      </p>
                    </div>
                    <div className="rounded-xl border border-white/5 bg-white/5 p-4">
                      <p className="text-[10px] uppercase tracking-[0.12em] text-white/40">
                        {locale === 'en' ? 'Depth' : '深度'}
                      </p>
                      <p className="mt-2 text-sm font-bold text-white">
                        {getDepthLabel(analysisDepth, locale)}
                      </p>
                    </div>
                    <div className="rounded-xl border border-white/5 bg-white/5 p-4">
                      <p className="text-[10px] uppercase tracking-[0.12em] text-white/40">
                        {locale === 'en' ? 'Experts Max' : '专家上限'}
                      </p>
                      <p className="mt-2 text-sm font-bold text-white">
                        {selectedDepthOption?.max_personas ?? '--'}
                      </p>
                    </div>
                    <div className="rounded-xl border border-white/5 bg-white/5 p-4">
                      <p className="text-[10px] uppercase tracking-[0.12em] text-white/40">
                        {locale === 'en' ? 'Rounds' : '轮数'}
                      </p>
                      <p className="mt-2 text-sm font-bold text-white">
                        {selectedDepthOption?.discussion_max_rounds ?? '--'}
                      </p>
                    </div>
                    <div className="rounded-xl border border-white/5 bg-white/5 p-4">
                      <p className="text-[10px] uppercase tracking-[0.12em] text-white/40">
                        {locale === 'en' ? 'Execution Cap' : '执行上限'}
                      </p>
                      <p className="mt-2 text-sm font-bold text-white">
                        {selectedDepthOption
                          ? `${Math.round(selectedDepthOption.execution_token_cap / 1000)}K`
                          : '--'}
                      </p>
                    </div>
                    <div className="rounded-xl border border-white/5 bg-white/5 p-4">
                      <p className="text-[10px] uppercase tracking-[0.12em] text-white/40">
                        {locale === 'en' ? 'Time Budget' : '时间预算'}
                      </p>
                      <p className="mt-2 text-sm font-bold text-white">
                        {selectedDepthOption
                          ? `${Math.round(selectedDepthOption.time_budget_seconds / 60)}${locale === 'en' ? ' min' : ' 分钟'}`
                          : '--'}
                      </p>
                    </div>
                  </div>

                  <div className="mt-4 flex flex-wrap gap-4 text-xs text-white/55">
                    <div className="rounded-full border border-white/10 px-3 py-1.5">
                      {locale === 'en' ? 'Answer reserve' : '答案保底'}:
                      {' '}
                      <span className="font-semibold text-white/80">
                        {selectedDepthOption
                          ? `${Math.round(selectedDepthOption.finalization_reserve_token_cap / 1000)}K`
                          : '--'}
                      </span>
                    </div>
                    <div className="rounded-full border border-white/10 px-3 py-1.5">
                      {locale === 'en' ? 'Fork exploration' : '分叉探索'}:
                      {' '}
                      <span className="font-semibold text-white/80">
                        {selectedDepthOption?.supports_fork
                          ? (locale === 'en' ? 'Enabled' : '开启')
                          : (locale === 'en' ? 'Disabled' : '关闭')}
                      </span>
                    </div>
                  </div>
                </div>
              </div>
            )}
          </div>
        </motion.div>

        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.1 }}
        >
          <div className="mb-6 flex items-center gap-4">
            <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-[#1a202c]">
              <Palette className="h-5 w-5 text-[#c3f5ff]" />
            </div>
            <h2 className="text-2xl font-serif italic text-white">
              {t('settings.uiSettings')}
            </h2>
          </div>

          <div className="rounded-2xl border border-white/5 bg-[#151a23] p-8 shadow-lg">
            <div className="mb-10 grid grid-cols-1 gap-8 lg:grid-cols-[1.2fr_1fr]">
              <div>
                <h3 className="mb-2 font-sans font-bold text-white">{t('settings.language')}</h3>
                <p className="mb-4 text-sm text-white/50">{t('settings.languageDesc')}</p>
                <Select
                  options={languageOptions}
                  value={interfaceLocale}
                  onChange={handleLocaleChange}
                />
              </div>

              <div className="rounded-2xl border border-white/5 bg-[#11161f] p-5">
                <p className="mb-2 text-[10px] font-bold uppercase tracking-[0.15em] text-white/50">
                  {locale === 'en' ? 'Sync Scope' : '同步范围'}
                </p>
                <p className="text-sm leading-6 text-white/60">
                  {isAuthenticated
                    ? (
                      locale === 'en'
                        ? 'Theme, interface language, and discussion defaults all sync to your account.'
                        : '主题、界面语言和讨论默认值都会同步到你的账号。'
                    )
                    : (
                      locale === 'en'
                        ? 'You are editing browser-local preferences right now. Sign in later if you want account-level sync.'
                        : '你当前修改的是浏览器本地偏好；之后登录即可切换到账号级同步。'
                    )}
                </p>
              </div>
            </div>

            <div>
              <h3 className="mb-4 text-[10px] font-bold uppercase tracking-[0.15em] text-white/50">
                {t('settings.luminanceMode')}
              </h3>
              <div className="grid grid-cols-1 gap-4 md:grid-cols-3">
                {themeOptions.map((option) => {
                  const Icon = option.icon;
                  const isActive = themeMode === option.value;
                  return (
                    <button
                      key={option.value}
                      type="button"
                      onClick={() => handleThemeChange(option.value)}
                      className={cn(
                        'relative overflow-hidden rounded-xl p-4 text-left transition-colors',
                        isActive
                          ? 'border border-[#c3f5ff]/50 bg-[#1e2430] shadow-[0_0_15px_rgba(195,245,255,0.05)]'
                          : 'border border-transparent bg-[#1e2430] hover:border-white/10',
                      )}
                    >
                      {isActive && <div className="absolute inset-0 bg-[#c3f5ff]/5" />}
                      <div className="relative z-10 flex items-center gap-3">
                        <Icon className={cn('h-5 w-5', isActive ? 'text-[#c3f5ff]' : 'text-white/50')} />
                        <span className={cn('text-sm font-medium', isActive ? 'text-white' : 'text-white/80')}>
                          {option.label}
                        </span>
                      </div>
                    </button>
                  );
                })}
              </div>
            </div>
          </div>
        </motion.div>
      </div>
    </div>
  );
}
