import { useState, useEffect } from 'react';
import { motion } from 'motion/react';
import { CreditCard, Check, Sparkles, Crown, Zap } from 'lucide-react';
import { cn } from '../lib/utils';
import { useLanguage } from '../hooks/useLanguage';
import { LOCAL_ONLY_MODE } from '../lib/runtime';
import { getPlans, getBillingInfo, type PricingPlan, type BillingInfo } from '../lib/api';

const planIcons: Record<string, typeof Zap> = {
  free: Zap,
  pro: Sparkles,
  max: Crown,
};

const planAccentColors: Record<string, string> = {
  free: '#64748b',
  pro: '#00e5ff',
  max: '#a78bfa',
};

function pickLocalized(locale: 'en' | 'zh', en?: string | null, zh?: string | null): string {
  if (locale === 'zh') {
    return zh ?? en ?? '';
  }
  return en ?? zh ?? '';
}

export default function Billing() {
  const { t, locale } = useLanguage();
  const [plans, setPlans] = useState<PricingPlan[]>([]);
  const [billing, setBilling] = useState<BillingInfo | null>(null);
  const [yearly, setYearly] = useState(false);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let active = true;

    const loadBilling = async () => {
      setLoading(true);

      const [plansResult, billingResult] = await Promise.allSettled([
        getPlans(),
        getBillingInfo(),
      ]);

      if (!active) return;

      setPlans(plansResult.status === 'fulfilled' ? plansResult.value : []);
      setBilling(billingResult.status === 'fulfilled' ? billingResult.value : null);
      setLoading(false);
    };

    loadBilling();

    return () => {
      active = false;
    };
  }, []);

  if (loading) {
    return (
      <div className="flex-1 flex items-center justify-center">
        <div className="w-6 h-6 border-2 border-[#00e5ff] border-t-transparent rounded-full animate-spin" />
      </div>
    );
  }

  const hasPlans = plans.length > 0;
  const currentPlan = billing ? plans.find((plan) => plan.id === billing.current_plan) : null;

  return (
    <div className="flex-1 overflow-y-auto no-scrollbar p-8 lg:p-12 z-10 w-full">
      <div className="max-w-6xl mx-auto">
        <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} className="mb-10">
          <div className="flex items-center gap-4 mb-3">
            <div className="w-10 h-10 rounded-lg bg-[#1a202c] flex items-center justify-center">
              <CreditCard className="w-5 h-5 text-[#c3f5ff]" />
            </div>
            <h2 className="text-2xl font-serif italic text-white">{t('billing.title')}</h2>
          </div>
          <p className="text-white/50 font-serif italic text-sm ml-14">{t('billing.subtitle')}</p>
        </motion.div>

        {billing && currentPlan && (
          <motion.div
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.05 }}
            className="mb-8 ml-14"
          >
            <div className="inline-flex items-center gap-2 bg-[#151a23] border border-white/5 rounded-full px-5 py-2">
              <div className="w-2 h-2 rounded-full bg-emerald-400 shadow-[0_0_6px_rgba(52,211,153,0.6)]" />
              <span className="text-xs font-sans text-white/60">{t('billing.currentPlan')}</span>
              <span className="text-xs font-bold text-white uppercase tracking-wider">
                {pickLocalized(locale, currentPlan.name, currentPlan.name_zh)}
              </span>
              <span className="text-xs text-white/40 border-l border-white/10 pl-2 ml-1">
                {billing.credits_remaining} / {billing.credits_monthly} {t('billing.credits')}
              </span>
              {billing.discussions_limit != null && (
                <span className="text-xs text-white/40 border-l border-white/10 pl-2 ml-1">
                  {billing.discussions_used} / {billing.discussions_limit} {t('billing.discussionsUsed')}
                </span>
              )}
            </div>
          </motion.div>
        )}

        {!hasPlans && (
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.1 }}
            className="rounded-3xl border border-white/5 bg-[#151a23] p-10 md:p-12"
          >
            <h3 className="text-2xl font-bold font-sans mb-3">{t('billing.emptyTitle')}</h3>
            <p className="max-w-2xl text-white/50 font-serif italic leading-relaxed">
              {LOCAL_ONLY_MODE ? t('billing.localModeNote') : t('billing.emptyBody')}
            </p>
          </motion.div>
        )}

        {hasPlans && (
          <>
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              transition={{ delay: 0.1 }}
              className="flex items-center justify-center gap-4 mb-10"
            >
              <span className={cn('text-sm font-sans', !yearly ? 'text-white font-bold' : 'text-white/50')}>
                {t('billing.monthly')}
              </span>
              <button
                onClick={() => setYearly(!yearly)}
                className="relative w-14 h-7 rounded-full bg-[#1e2430] border border-white/10 flex items-center px-1 cursor-pointer transition-colors"
              >
                <motion.div
                  animate={{ x: yearly ? 24 : 0 }}
                  transition={{ type: 'spring', stiffness: 500, damping: 30 }}
                  className="w-5 h-5 rounded-full bg-[#00e5ff] shadow-[0_0_10px_rgba(0,229,255,0.5)]"
                />
              </button>
              <span className={cn('text-sm font-sans', yearly ? 'text-white font-bold' : 'text-white/50')}>
                {t('billing.yearly')}
              </span>
              {yearly && (
                <span className="text-[10px] font-bold text-emerald-400 bg-emerald-400/10 rounded-full px-2 py-0.5 tracking-wider uppercase">
                  {t('billing.savePercent')}
                </span>
              )}
            </motion.div>

            <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
              {plans.map((plan, idx) => {
                const Icon = planIcons[plan.id] ?? Zap;
                const accent = planAccentColors[plan.id] ?? '#00e5ff';
                const isCurrent = billing?.current_plan === plan.id;
                const price = yearly ? plan.price_yearly : plan.price_monthly;
                const planName = pickLocalized(locale, plan.name, plan.name_zh);
                const planDesc = pickLocalized(locale, plan.description, plan.description_zh);
                const badge = pickLocalized(locale, plan.badge, plan.badge_zh);

                return (
                  <motion.div
                    key={plan.id}
                    initial={{ opacity: 0, y: 30 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ delay: 0.15 + idx * 0.1 }}
                    className={cn(
                      'relative rounded-2xl p-[1px] overflow-hidden',
                      plan.highlighted && 'shadow-[0_0_40px_rgba(0,229,255,0.1)]',
                    )}
                  >
                    {plan.highlighted && (
                      <div className="absolute inset-0 rounded-2xl bg-gradient-to-b from-[#00e5ff]/30 via-transparent to-[#00e5ff]/10" />
                    )}

                    <div
                      className={cn(
                        'relative bg-[#151a23] rounded-2xl p-8 border flex flex-col h-full',
                        plan.highlighted ? 'border-[#00e5ff]/20' : 'border-white/5',
                      )}
                    >
                      {badge && (
                        <div
                          className="absolute -top-px left-1/2 -translate-x-1/2 px-4 py-1 rounded-b-lg text-[10px] font-bold tracking-wider uppercase"
                          style={{ backgroundColor: `${accent}20`, color: accent }}
                        >
                          {badge}
                        </div>
                      )}

                      <div className="flex items-center gap-3 mb-4 mt-2">
                        <div
                          className="w-10 h-10 rounded-xl flex items-center justify-center"
                          style={{ backgroundColor: `${accent}15` }}
                        >
                          <Icon className="w-5 h-5" style={{ color: accent }} />
                        </div>
                        <div>
                          <h3 className="text-lg font-bold text-white">{planName}</h3>
                        </div>
                      </div>

                      <div className="mb-4">
                        {price === 0 ? (
                          <div className="flex items-baseline gap-1">
                            <span className="text-4xl font-bold text-white">{t('billing.free')}</span>
                          </div>
                        ) : (
                          <div className="flex items-baseline gap-1">
                            <span className="text-lg text-white/50">$</span>
                            <span className="text-4xl font-bold text-white">
                              {yearly ? Math.round(plan.price_yearly / 12) : price}
                            </span>
                            <span className="text-sm text-white/40 font-serif italic">
                              / {t('billing.perMonth')}
                            </span>
                          </div>
                        )}
                        {yearly && price > 0 && (
                          <p className="text-xs text-white/40 mt-1">
                            ${plan.price_yearly} / {t('billing.perYear')}
                          </p>
                        )}
                      </div>

                      <p className="text-sm text-white/50 font-serif italic mb-6 leading-relaxed min-h-[3rem]">
                        {planDesc}
                      </p>

                      <div className="mb-6 min-h-[4.5rem]">
                        <h4 className="text-[10px] font-sans font-bold text-white/50 tracking-[0.15em] uppercase mb-3">
                          {t('billing.availableModels')}
                        </h4>
                        <div className="flex flex-wrap gap-2">
                          {plan.models.map((model) => (
                            <span
                              key={model.id}
                              className="text-[11px] font-mono px-2.5 py-1 rounded-lg bg-[#1e2430] border border-white/5 text-white/70"
                            >
                              {model.label}
                            </span>
                          ))}
                        </div>
                      </div>

                      <div className="flex-1 mb-8">
                        <ul className="space-y-3">
                          {plan.features.map((feature, featureIndex) => (
                            <li key={featureIndex} className="flex items-start gap-3">
                              <Check className="w-4 h-4 mt-0.5 shrink-0" style={{ color: accent }} />
                              <span className="text-sm text-white/70">
                                {pickLocalized(locale, feature.text, feature.text_zh)}
                              </span>
                            </li>
                          ))}
                        </ul>
                      </div>

                      <button
                        className={cn(
                          'w-full py-3.5 rounded-xl font-bold text-sm transition-all duration-300',
                          isCurrent
                            ? 'bg-[#1e2430] border border-white/10 text-white/50 cursor-default'
                            : plan.highlighted
                              ? 'bg-[#00e5ff] text-black hover:bg-[#00cce6] shadow-[0_0_20px_rgba(0,229,255,0.2)]'
                              : 'bg-[#1e2430] border border-white/10 text-white hover:border-white/20 hover:bg-[#252d3d]',
                        )}
                        disabled={isCurrent}
                      >
                        {isCurrent
                          ? t('billing.currentPlanBtn')
                          : plan.price_monthly === 0
                            ? t('billing.getStarted')
                            : t('billing.upgrade')}
                      </button>
                    </div>
                  </motion.div>
                );
              })}
            </div>

            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              transition={{ delay: 0.6 }}
              className="mt-12 text-center"
            >
              <p className="text-xs text-white/30 font-serif italic">{t('billing.note')}</p>
            </motion.div>
          </>
        )}
      </div>
    </div>
  );
}
