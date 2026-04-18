import { useEffect, useState } from 'react';
import { motion } from 'motion/react';
import { useNavigate } from 'react-router-dom';
import {
  ArrowLeft,
  ArrowRight,
  ChevronLeft,
  ChevronRight,
  Clock3,
  Pencil,
  Settings2,
  Sparkles,
} from 'lucide-react';
import { Select } from '../components/ui';
import { SYSTEM_PERSONAS, LIMITS } from '../data/personas';
import { useLanguage } from '../hooks/useLanguage';
import * as api from '../lib/api';
import { resolveAvatarSrc } from '../lib/avatar';
import {
  readLocalDiscussionPreferences,
  resolveDiscussionDefaults,
} from '../lib/discussionPreferences';
import { AUTH_ENABLED } from '../lib/runtime';
import { cn } from '../lib/utils';

type AnalysisDepthId = 'quick' | 'standard' | 'deep';

function getDepthLabel(depth: AnalysisDepthId, locale: 'zh' | 'en'): string {
  if (depth === 'quick') {
    return locale === 'en' ? 'Quick' : '快速';
  }
  if (depth === 'deep') {
    return locale === 'en' ? 'Deep' : '深入';
  }
  return locale === 'en' ? 'Standard' : '标准';
}

export default function NewDiscussion() {
  const navigate = useNavigate();
  const { t, locale } = useLanguage();
  const [step, setStep] = useState(1);
  const [question, setQuestion] = useState('');
  const [selected, setSelected] = useState<string[]>([]);
  const [model, setModel] = useState('');
  const [analysisDepth, setAnalysisDepth] = useState<AnalysisDepthId>('standard');
  const [discussionLocale, setDiscussionLocale] = useState<'zh' | 'en'>('zh');
  const [availableModels, setAvailableModels] = useState<api.ModelOption[]>([]);
  const [availableDepths, setAvailableDepths] = useState<api.AnalysisDepthOption[]>([]);
  const [launching, setLaunching] = useState(false);
  const [error, setError] = useState('');
  const [settingsLoading, setSettingsLoading] = useState(true);
  const [settingsError, setSettingsError] = useState('');
  const [expertPage, setExpertPage] = useState(0);

  const isEnglish = locale === 'en';
  const expertsPerPage = 6;
  const totalExpertPages = Math.ceil(SYSTEM_PERSONAS.length / expertsPerPage);
  const pagedExperts = SYSTEM_PERSONAS.slice(
    expertPage * expertsPerPage,
    (expertPage + 1) * expertsPerPage,
  );
  const questionValid = question.trim().length >= LIMITS.QUESTION_MIN;
  const selectedDepthOption = availableDepths.find((depth) => depth.id === analysisDepth)
    ?? availableDepths[0]
    ?? null;
  const maxSelectableExperts = selectedDepthOption?.max_personas ?? LIMITS.PERSONA_MAX;
  const depthRounds = selectedDepthOption?.discussion_max_rounds ?? 0;
  const depthTimeBudgetMinutes = Math.round((selectedDepthOption?.time_budget_seconds ?? 0) / 60);
  const depthExecutionCapLabel = selectedDepthOption
    ? `${Math.round(selectedDepthOption.execution_token_cap / 1000)}K`
    : '--';
  const depthReserveCapLabel = selectedDepthOption
    ? `${Math.round(selectedDepthOption.finalization_reserve_token_cap / 1000)}K`
    : '--';
  const selectedModel = availableModels.find((item) => item.id === model);
  const selectedExperts = SYSTEM_PERSONAS.filter((expert) => selected.includes(expert.id));

  function buildExpertLimitMessage(limit: number): string {
    return isEnglish
      ? `This depth allows up to ${limit} experts. Remove one or choose a deeper preset.`
      : `当前深度最多允许 ${limit} 位专家，请删除一张卡片或提高分析深度。`;
  }

  useEffect(() => {
    let cancelled = false;

    async function loadSettings() {
      setSettingsLoading(true);
      setSettingsError('');

      try {
        const runtimeSettings = await api.getSettings();
        let preferenceOverrides = readLocalDiscussionPreferences();

        if (AUTH_ENABLED && api.getToken()) {
          try {
            const userSettings = await api.getMySettings();
            preferenceOverrides = userSettings.discussion_preferences;
          } catch (err) {
            if (!cancelled) {
              setSettingsError(
                err instanceof api.ApiError
                  ? err.message
                  : (
                    isEnglish
                      ? 'Failed to load synced defaults. Using local values instead.'
                      : '加载账号默认值失败，当前先使用本地值。'
                  ),
              );
            }
          }
        }

        if (cancelled) {
          return;
        }

        const defaults = resolveDiscussionDefaults(runtimeSettings, preferenceOverrides);
        setAvailableModels(runtimeSettings.models);
        setAvailableDepths(runtimeSettings.analysis_depths);
        setModel(defaults.selectedModel);
        setAnalysisDepth(defaults.analysisDepth);
        setDiscussionLocale(defaults.discussionLocale);
      } catch (err) {
        if (cancelled) {
          return;
        }
        setSettingsError(
          err instanceof api.ApiError
            ? err.message
            : (
              isEnglish
                ? 'Failed to load server configuration.'
                : '加载后端配置失败。'
            ),
        );
      } finally {
        if (!cancelled) {
          setSettingsLoading(false);
        }
      }
    }

    void loadSettings();
    return () => {
      cancelled = true;
    };
  }, [isEnglish]);

  function handleDepthChange(value: string) {
    const nextDepth = value as AnalysisDepthId;
    const nextOption = availableDepths.find((depth) => depth.id === nextDepth);
    setAnalysisDepth(nextDepth);

    if (nextOption && selected.length > nextOption.max_personas) {
      setError(buildExpertLimitMessage(nextOption.max_personas));
      return;
    }

    setError('');
  }

  function toggleExpert(id: string) {
    setSelected((prev) => {
      if (prev.includes(id)) {
        setError('');
        return prev.filter((value) => value !== id);
      }
      if (prev.length >= maxSelectableExperts) {
        setError(buildExpertLimitMessage(maxSelectableExperts));
        return prev;
      }
      setError('');
      return [...prev, id];
    });
  }

  async function handleStart() {
    setError('');

    if (!model) {
      setError(isEnglish ? 'Please choose a model.' : '请选择一个模型。');
      return;
    }

    if (selected.length > maxSelectableExperts) {
      setError(buildExpertLimitMessage(maxSelectableExperts));
      return;
    }

    setLaunching(true);
    try {
      const response = await api.createDiscussion({
        question: question.trim(),
        persona_ids: selected,
        config: {
          selected_model: model,
          analysis_depth: analysisDepth,
          discussion_locale: discussionLocale,
        },
      });
      navigate(`/discussion/${response.discussion_id}`);
    } catch (err) {
      setError(err instanceof api.ApiError ? err.message : t('newDiscussion.createError'));
    } finally {
      setLaunching(false);
    }
  }

  const modelOptions = availableModels.map((value) => ({
    value: value.id,
    label: value.label,
    description: isEnglish ? 'Backend allowlisted model' : '后端白名单模型',
  }));

  const depthOptions = availableDepths.map((value) => ({
    value: value.id,
    label: getDepthLabel(value.id, locale),
    description: isEnglish
      ? `${value.max_personas} experts · ${value.discussion_max_rounds} rounds · ${Math.round(value.time_budget_seconds / 60)}m`
      : `${value.max_personas} 位专家 · ${value.discussion_max_rounds} 轮 · ${Math.round(value.time_budget_seconds / 60)} 分钟`,
  }));

  const discussionLanguageOptions = [
    {
      value: 'zh',
      label: isEnglish ? 'Chinese' : '中文',
      description: isEnglish ? 'Discussion output in Simplified Chinese' : '讨论输出为简体中文',
    },
    {
      value: 'en',
      label: 'English',
      description: isEnglish ? 'Discussion output in English' : '讨论输出为英文',
    },
  ];

  const analysisDepthLabel = getDepthLabel(analysisDepth, locale);
  const discussionLanguageLabel = discussionLocale === 'zh'
    ? (isEnglish ? 'Chinese' : '中文')
    : 'English';

  return (
    <div className="flex-1 overflow-y-auto no-scrollbar bg-[#0b0f17] p-8 text-white lg:p-12">
      <div className="mx-auto max-w-6xl">
        <div className="mb-10">
          <div className="mb-6 flex items-center gap-2">
            <span className="text-[10px] font-bold uppercase tracking-[0.2em] text-white/50">
              {t('newDiscussion.wizardMode')}
            </span>
            <div className="flex gap-1.5">
              {[1, 2, 3].map((value) => (
                <div
                  key={value}
                  className={cn('h-2 w-2 rounded-full', value <= step ? 'bg-white' : 'bg-white/20')}
                />
              ))}
            </div>
          </div>
          <motion.h1
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            className="mb-2 text-4xl font-bold tracking-tight"
          >
            {step === 1 && t('newDiscussion.step1.title')}
            {step === 2 && t('newDiscussion.step2.title')}
            {step === 3 && t('newDiscussion.step3.title')}
          </motion.h1>
          <motion.p
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.1 }}
            className="text-xl font-serif italic text-white/50"
          >
            {step === 1 && t('newDiscussion.step1.subtitle')}
            {step === 2 && t('newDiscussion.step2.subtitle')}
            {step === 3 && t('newDiscussion.step3.subtitle')}
          </motion.p>
        </div>

        {step === 1 && (
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.2 }}
            className="max-w-3xl"
          >
            <textarea
              value={question}
              onChange={(event) => setQuestion(event.target.value)}
              placeholder={t('newDiscussion.placeholder')}
              className="h-48 w-full resize-none rounded-2xl border border-white/10 bg-[#151a23] p-6 text-lg text-white placeholder:text-white/30 focus:border-[#00e5ff]/50 focus:outline-none"
            />
            <div className="mt-6">
              <p className="mb-3 text-[10px] font-bold uppercase tracking-[0.15em] text-white/40">
                {t('newDiscussion.goodExamples')}
              </p>
              <div className="space-y-2">
                {[t('newDiscussion.example1'), t('newDiscussion.example2'), t('newDiscussion.example3')].map((example) => (
                  <button
                    key={example}
                    type="button"
                    onClick={() => setQuestion(example)}
                    className="block text-left text-sm italic text-white/50 transition-colors hover:text-white/80"
                  >
                    → "{example}"
                  </button>
                ))}
              </div>
            </div>
            <div className="mt-10 flex justify-end">
              <button
                type="button"
                onClick={() => questionValid && setStep(2)}
                disabled={!questionValid}
                className="flex items-center gap-2 rounded-xl bg-[#00e5ff] px-8 py-3 font-bold text-black transition-colors hover:bg-[#00cce6] disabled:cursor-not-allowed disabled:opacity-30"
              >
                {t('newDiscussion.next')} <ArrowRight className="h-4 w-4" />
              </button>
            </div>
          </motion.div>
        )}

        {step === 2 && (
          <div className="flex flex-col gap-8 lg:flex-row">
            <div className="flex-1 space-y-10">
              <motion.div
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.2 }}
              >
                <h3 className="mb-4 text-[10px] font-bold uppercase tracking-[0.2em] text-white/40">
                  {t('newDiscussion.primaryInquiry')}
                </h3>
                <div className="flex items-start gap-4">
                  <div className="flex-1 border-l-2 border-[#00e5ff] bg-transparent py-2 pl-6">
                    <p className="text-2xl font-serif italic leading-relaxed text-white/90">
                      "{question.trim()}"
                    </p>
                  </div>
                  <button
                    type="button"
                    onClick={() => setStep(1)}
                    className="mt-2 flex shrink-0 items-center gap-1.5 rounded-lg border border-white/10 px-3 py-1.5 text-xs font-bold text-white/60 transition-colors hover:border-white/30 hover:text-white"
                  >
                    <Pencil className="h-3 w-3" /> {t('newDiscussion.edit')}
                  </button>
                </div>
              </motion.div>

              <motion.div
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.3 }}
              >
                <div className="mb-6 flex items-end justify-between">
                  <div>
                    <h2 className="mb-1 text-2xl font-bold">{t('newDiscussion.selectExperts')}</h2>
                    <div className="flex items-center gap-2 text-sm text-white/60">
                      <div className="flex h-3 w-3 items-center justify-center rounded-sm bg-[#00e5ff]/20">
                        <div className="h-1 w-1 rounded-full bg-[#00e5ff]" />
                      </div>
                      {t('newDiscussion.selected')}: {selected.length}/{maxSelectableExperts}
                    </div>
                  </div>
                </div>

                <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
                  {pagedExperts.map((expert) => {
                    const isSelected = selected.includes(expert.id);
                    const expertName = locale === 'en' ? (expert.nameEn ?? expert.name) : expert.name;
                    const tags = locale === 'en' ? (expert.tagsEn ?? expert.tags) : expert.tags;
                    const avatarSrc = resolveAvatarSrc(expert.avatar, expert.id, expertName);

                    return (
                      <button
                        key={expert.id}
                        type="button"
                        onClick={() => toggleExpert(expert.id)}
                        className={cn(
                          'relative overflow-hidden rounded-2xl p-5 text-left transition-colors',
                          isSelected
                            ? 'border border-[#00e5ff] bg-[#151a23] shadow-[0_0_20px_rgba(0,229,255,0.1)]'
                            : 'border border-white/5 bg-[#151a23] hover:border-white/20',
                        )}
                      >
                        {isSelected && <div className="absolute inset-0 bg-[#00e5ff]/5" />}
                        <div className="relative z-10">
                          <div className="mb-4 flex items-start justify-between">
                            <img
                              src={avatarSrc}
                              className={cn(
                                'h-12 w-12 rounded-xl border border-white/10 object-cover',
                                !isSelected && 'grayscale opacity-70',
                              )}
                              alt={expertName}
                              referrerPolicy="no-referrer"
                            />
                            <span className="rounded border border-white/5 bg-white/5 px-2 py-0.5 text-[10px] capitalize text-white/50">
                              {expert.domain}
                            </span>
                          </div>
                          <h3 className={cn('mb-0.5 text-lg font-bold', isSelected ? 'text-white' : 'text-white/80')}>
                            {expertName}
                          </h3>
                          <p className={cn('mb-4 text-sm', isSelected ? 'text-white/50' : 'text-white/40')}>
                            {expert.role}
                          </p>
                          <div className="flex flex-wrap gap-2">
                            {tags.map((tag) => (
                              <span
                                key={tag}
                                className="rounded border border-white/5 bg-white/5 px-2 py-1 text-[10px] text-white/60"
                              >
                                {tag}
                              </span>
                            ))}
                          </div>
                        </div>
                      </button>
                    );
                  })}
                </div>
              </motion.div>

              {totalExpertPages > 1 && (
                <div className="flex items-center justify-center gap-4">
                  <button
                    type="button"
                    onClick={() => setExpertPage((current) => Math.max(0, current - 1))}
                    disabled={expertPage === 0}
                    className="flex items-center gap-1.5 rounded-xl border border-white/10 bg-[#151a23] px-5 py-2.5 font-bold text-white/70 transition-colors hover:bg-white/5 disabled:cursor-not-allowed disabled:opacity-30"
                  >
                    <ChevronLeft className="h-4 w-4" /> {t('newDiscussion.prevPage')}
                  </button>
                  <span className="text-sm text-white/50">
                    {expertPage + 1} / {totalExpertPages}
                  </span>
                  <button
                    type="button"
                    onClick={() => setExpertPage((current) => Math.min(totalExpertPages - 1, current + 1))}
                    disabled={expertPage === totalExpertPages - 1}
                    className="flex items-center gap-1.5 rounded-xl border border-white/10 bg-[#151a23] px-5 py-2.5 font-bold text-white/70 transition-colors hover:bg-white/5 disabled:cursor-not-allowed disabled:opacity-30"
                  >
                    {t('newDiscussion.nextPage')} <ChevronRight className="h-4 w-4" />
                  </button>
                </div>
              )}
            </div>

            <motion.div
              initial={{ opacity: 0, x: 20 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ delay: 0.4 }}
              className="w-full shrink-0 lg:w-80"
            >
              <div className="sticky top-8 rounded-2xl border border-white/5 bg-[#151a23] p-6">
                <div className="mb-8 flex items-center gap-3">
                  <Settings2 className="h-5 w-5 text-white/70" />
                  <h2 className="text-xl font-bold">{t('newDiscussion.parameters')}</h2>
                </div>

                <div className="mb-8 space-y-6">
                  <div>
                    <label className="mb-3 block text-[10px] font-bold uppercase tracking-[0.15em] text-white/50">
                      {t('newDiscussion.llmModel')}
                    </label>
                    <Select
                      options={modelOptions}
                      value={model}
                      onChange={(value) => {
                        setModel(value);
                        setError('');
                      }}
                      placeholder={settingsLoading ? t('newDiscussion.loadingModel') : t('newDiscussion.noModel')}
                    />
                  </div>

                  <div>
                    <label className="mb-3 block text-[10px] font-bold uppercase tracking-[0.15em] text-white/50">
                      {isEnglish ? 'Analysis Depth' : '分析深度'}
                    </label>
                    <Select
                      options={depthOptions}
                      value={analysisDepth}
                      onChange={handleDepthChange}
                    />
                  </div>

                  <div>
                    <label className="mb-3 block text-[10px] font-bold uppercase tracking-[0.15em] text-white/50">
                      {isEnglish ? 'Discussion Language' : '讨论语言'}
                    </label>
                    <Select
                      options={discussionLanguageOptions}
                      value={discussionLocale}
                      onChange={(value) => {
                        setDiscussionLocale(value as 'zh' | 'en');
                        setError('');
                      }}
                    />
                  </div>
                </div>

                <div className="mb-6 rounded-2xl border border-white/10 bg-[#11161f] p-4">
                  <div className="mb-4 flex items-center gap-2 text-sm font-semibold text-white/85">
                    <Sparkles className="h-4 w-4 text-[#00e5ff]" />
                    {isEnglish ? 'Resolved Runtime Profile' : '当前运行档位'}
                  </div>

                  <div className="grid grid-cols-2 gap-3 text-sm">
                    <div className="rounded-xl border border-white/5 bg-white/5 p-3">
                      <p className="text-[10px] uppercase tracking-[0.12em] text-white/40">
                        {isEnglish ? 'Depth' : '深度'}
                      </p>
                      <p className="mt-1 font-bold text-white">{analysisDepthLabel}</p>
                    </div>
                    <div className="rounded-xl border border-white/5 bg-white/5 p-3">
                      <p className="text-[10px] uppercase tracking-[0.12em] text-white/40">
                        {isEnglish ? 'Experts Max' : '专家上限'}
                      </p>
                      <p className="mt-1 font-bold text-white">{maxSelectableExperts}</p>
                    </div>
                    <div className="rounded-xl border border-white/5 bg-white/5 p-3">
                      <p className="text-[10px] uppercase tracking-[0.12em] text-white/40">
                        {isEnglish ? 'Rounds' : '轮数'}
                      </p>
                      <p className="mt-1 font-bold text-white">{depthRounds}</p>
                    </div>
                    <div className="rounded-xl border border-white/5 bg-white/5 p-3">
                      <p className="text-[10px] uppercase tracking-[0.12em] text-white/40">
                        {isEnglish ? 'Time Budget' : '时间预算'}
                      </p>
                      <p className="mt-1 font-bold text-white">
                        {depthTimeBudgetMinutes}
                        {isEnglish ? ' min' : ' 分钟'}
                      </p>
                    </div>
                    <div className="rounded-xl border border-white/5 bg-white/5 p-3">
                      <p className="text-[10px] uppercase tracking-[0.12em] text-white/40">
                        {isEnglish ? 'Execution Cap' : '执行上限'}
                      </p>
                      <p className="mt-1 font-bold text-white">{depthExecutionCapLabel}</p>
                    </div>
                    <div className="rounded-xl border border-white/5 bg-white/5 p-3">
                      <p className="text-[10px] uppercase tracking-[0.12em] text-white/40">
                        {isEnglish ? 'Answer Reserve' : '答案保底'}
                      </p>
                      <p className="mt-1 font-bold text-white">{depthReserveCapLabel}</p>
                    </div>
                  </div>

                  <div className="mt-4 flex items-center justify-between text-xs text-white/55">
                    <span>{isEnglish ? 'Fork exploration' : '分叉探索'}</span>
                    <span className="font-semibold text-white/80">
                      {selectedDepthOption?.supports_fork
                        ? (isEnglish ? 'Enabled' : '开启')
                        : (isEnglish ? 'Disabled' : '关闭')}
                    </span>
                  </div>
                </div>

                <div className="mb-6 space-y-3 border-t border-white/10 pt-6">
                  <div className="flex items-center justify-between text-sm">
                    <span className="font-serif italic text-white/50">{t('newDiscussion.activeExperts')}</span>
                    <span className="font-bold">{String(selected.length).padStart(2, '0')}</span>
                  </div>
                  <div className="flex items-center justify-between text-sm">
                    <span className="font-serif italic text-white/50">{t('newDiscussion.protocol')}</span>
                    <span className="font-bold text-white/90">{t('newDiscussion.sixHats')}</span>
                  </div>
                </div>

                {settingsError && (
                  <p className="mb-4 rounded-xl border border-amber-400/20 bg-amber-400/10 px-3 py-2 text-xs text-amber-200">
                    {settingsError}
                  </p>
                )}

                {error && (
                  <p className="mb-4 rounded-xl border border-red-500/20 bg-red-500/10 px-3 py-2 text-xs text-red-300">
                    {error}
                  </p>
                )}

                <button
                  type="button"
                  onClick={() => {
                    if (selected.length > maxSelectableExperts) {
                      setError(buildExpertLimitMessage(maxSelectableExperts));
                      return;
                    }
                    if (selected.length >= LIMITS.PERSONA_MIN && model) {
                      setError('');
                      setStep(3);
                    }
                  }}
                  disabled={selected.length < LIMITS.PERSONA_MIN || !model || selected.length > maxSelectableExperts}
                  className="w-full rounded-xl bg-[#00e5ff] py-3 font-bold text-black transition-colors hover:bg-[#00cce6] disabled:cursor-not-allowed disabled:opacity-30"
                >
                  {t('newDiscussion.confirmStart')} <ArrowRight className="ml-1 inline h-4 w-4" />
                </button>
              </div>
            </motion.div>
          </div>
        )}

        {step === 3 && (
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.2 }}
            className="max-w-3xl"
          >
            <div className="mb-8 rounded-2xl border border-white/5 bg-[#151a23] p-8">
              <h3 className="mb-4 text-[10px] font-bold uppercase tracking-[0.2em] text-white/40">
                {t('newDiscussion.summary')}
              </h3>

              <div className="space-y-6">
                <div>
                  <p className="mb-1 text-sm font-serif italic text-white/50">
                    {t('newDiscussion.question')}
                  </p>
                  <p className="text-lg font-serif italic text-white/90">"{question.trim()}"</p>
                </div>

                <div>
                  <p className="mb-2 text-sm font-serif italic text-white/50">
                    {t('newDiscussion.experts')} ({selected.length})
                  </p>
                  <div className="flex flex-wrap gap-3">
                    {selectedExperts.map((expert) => (
                      <div
                        key={expert.id}
                        className="flex items-center gap-2 rounded-lg border border-white/5 bg-[#1e2430] px-3 py-2"
                      >
                        <img
                          src={resolveAvatarSrc(
                            expert.avatar,
                            expert.id,
                            locale === 'en' ? (expert.nameEn ?? expert.name) : expert.name,
                          )}
                          className="h-6 w-6 rounded object-cover"
                          alt={locale === 'en' ? (expert.nameEn ?? expert.name) : expert.name}
                          referrerPolicy="no-referrer"
                        />
                        <span className="text-sm font-medium">
                          {locale === 'en' ? (expert.nameEn ?? expert.name) : expert.name}
                        </span>
                      </div>
                    ))}
                  </div>
                </div>

                <div className="grid grid-cols-2 gap-4 border-t border-white/10 pt-4 md:grid-cols-3">
                  <div>
                    <p className="mb-1 text-xs font-serif italic text-white/50">
                      {t('newDiscussion.model')}
                    </p>
                    <p className="text-sm font-bold">
                      {selectedModel?.label || model || t('newDiscussion.notLoaded')}
                    </p>
                  </div>
                  <div>
                    <p className="mb-1 text-xs font-serif italic text-white/50">
                      {isEnglish ? 'Analysis Depth' : '分析深度'}
                    </p>
                    <p className="text-sm font-bold">{analysisDepthLabel}</p>
                  </div>
                  <div>
                    <p className="mb-1 text-xs font-serif italic text-white/50">
                      {isEnglish ? 'Discussion Language' : '讨论语言'}
                    </p>
                    <p className="text-sm font-bold">{discussionLanguageLabel}</p>
                  </div>
                  <div>
                    <p className="mb-1 text-xs font-serif italic text-white/50">
                      {isEnglish ? 'Rounds' : '轮数'}
                    </p>
                    <p className="text-sm font-bold">{depthRounds}</p>
                  </div>
                  <div>
                    <p className="mb-1 text-xs font-serif italic text-white/50">
                      {isEnglish ? 'Time Budget' : '时间预算'}
                    </p>
                    <p className="text-sm font-bold">
                      {depthTimeBudgetMinutes}
                      {isEnglish ? ' min' : ' 分钟'}
                    </p>
                  </div>
                  <div>
                    <p className="mb-1 text-xs font-serif italic text-white/50">
                      {isEnglish ? 'Execution Cap' : '执行上限'}
                    </p>
                    <p className="text-sm font-bold">{depthExecutionCapLabel}</p>
                  </div>
                </div>
              </div>
            </div>

            <div className="flex gap-4">
              <button
                type="button"
                onClick={() => setStep(2)}
                className="flex items-center gap-2 rounded-xl border border-white/10 bg-[#151a23] px-6 py-3 font-bold text-white/70 transition-colors hover:bg-white/5"
              >
                <ArrowLeft className="h-4 w-4" /> {t('newDiscussion.back')}
              </button>
              <button
                type="button"
                onClick={handleStart}
                disabled={launching || !model || selected.length > maxSelectableExperts}
                className="flex-1 rounded-xl bg-[#00e5ff] py-4 font-bold text-black transition-colors hover:bg-[#00cce6] disabled:cursor-not-allowed disabled:opacity-50"
              >
                {launching ? t('newDiscussion.launching') : t('newDiscussion.startDiscussion')}
              </button>
            </div>
            {error && (
              <div className="mt-4 rounded-lg border border-red-500/20 bg-red-500/10 px-4 py-3 text-sm text-red-400">
                {error}
              </div>
            )}
            <p className="mt-4 flex items-center justify-center gap-2 text-center text-xs italic text-white/40">
              <Clock3 className="h-3.5 w-3.5" />
              {isEnglish ? 'Estimated spin-up time: ~12 seconds' : '预计启动时间：约 12 秒'}
            </p>
          </motion.div>
        )}
      </div>
    </div>
  );
}
