import { useEffect, useMemo, useState } from 'react';
import { motion } from 'motion/react';
import { Link } from 'react-router-dom';
import { Activity, Users, Cpu } from 'lucide-react';
import { AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts';
import { cn } from '../lib/utils';
import { useLanguage } from '../hooks/useLanguage';
import * as api from '../lib/api';

const ACTIVITY_DAYS = 7;

function formatDayKey(date: Date) {
  const year = date.getFullYear();
  const month = `${date.getMonth() + 1}`.padStart(2, '0');
  const day = `${date.getDate()}`.padStart(2, '0');
  return `${year}-${month}-${day}`;
}

export default function Overview() {
  const { t, locale } = useLanguage();
  const [items, setItems] = useState<api.ArchiveSummary[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let active = true;

    const loadOverview = async () => {
      setLoading(true);
      try {
        const response = await api.getArchive({ limit: 100, offset: 0 });
        if (!active) return;

        const sortedItems = [...response.items].sort(
          (a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime(),
        );

        setItems(sortedItems);
        setTotal(response.total);
      } catch {
        if (!active) return;
        setItems([]);
        setTotal(0);
      } finally {
        if (active) {
          setLoading(false);
        }
      }
    };

    loadOverview();

    return () => {
      active = false;
    };
  }, []);

  const dateLabelFormatter = useMemo(
    () =>
      new Intl.DateTimeFormat(locale === 'zh' ? 'zh-CN' : 'en-US', {
        month: 'numeric',
        day: 'numeric',
      }),
    [locale],
  );

  const fullDateFormatter = useMemo(
    () =>
      new Intl.DateTimeFormat(locale === 'zh' ? 'zh-CN' : 'en-US', {
        year: 'numeric',
        month: '2-digit',
        day: '2-digit',
      }),
    [locale],
  );

  const activityData = useMemo(() => {
    const today = new Date();
    today.setHours(0, 0, 0, 0);

    const buckets = Array.from({ length: ACTIVITY_DAYS }, (_, index) => {
      const date = new Date(today);
      date.setDate(today.getDate() - (ACTIVITY_DAYS - 1 - index));
      return {
        key: formatDayKey(date),
        name: dateLabelFormatter.format(date),
        discussions: 0,
      };
    });

    const bucketMap = new Map(buckets.map((bucket) => [bucket.key, bucket]));

    for (const item of items) {
      const createdAt = new Date(item.created_at);
      if (Number.isNaN(createdAt.getTime())) continue;

      const bucket = bucketMap.get(formatDayKey(createdAt));
      if (bucket) {
        bucket.discussions += 1;
      }
    }

    return buckets;
  }, [dateLabelFormatter, items]);

  const activePersonas = useMemo(() => {
    const personaIds = new Set<string>();

    for (const item of items) {
      for (const personaId of item.personas) {
        personaIds.add(personaId);
      }
    }

    return personaIds.size;
  }, [items]);

  const recentDiscussions = useMemo(() => items.slice(0, 3), [items]);
  const discussionsLast7Days = useMemo(
    () => activityData.reduce((sum, bucket) => sum + bucket.discussions, 0),
    [activityData],
  );
  const hasActivity = activityData.some((bucket) => bucket.discussions > 0);

  const stats = [
    {
      title: t('overview.totalDiscussions'),
      value: loading ? '--' : String(total),
      note:
        total > 0
          ? t('overview.discussionsLast7Days', { count: discussionsLast7Days })
          : t('overview.noArchiveData'),
      icon: Activity,
      color: 'text-primary',
    },
    {
      title: t('overview.activePersonas'),
      value: loading ? '--' : String(activePersonas),
      note:
        activePersonas > 0
          ? t('overview.personasUsed', { count: activePersonas })
          : t('overview.noArchiveData'),
      icon: Users,
      color: 'text-secondary',
    },
    {
      title: t('overview.tokenBudgetUsed'),
      value: '--',
      note: t('overview.tokenMetricUnavailable'),
      icon: Cpu,
      color: 'text-tertiary',
    },
  ];

  const formatDisplayDate = (value: string) => {
    const date = new Date(value);
    if (Number.isNaN(date.getTime())) {
      return value.slice(0, 10);
    }
    return fullDateFormatter.format(date);
  };

  return (
    <div className="flex-1 overflow-y-auto no-scrollbar p-8 z-10">
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.1 }}
        className="mb-8"
      >
        <h2 className="text-3xl font-bold font-sans mb-2">{t('overview.welcome')}</h2>
        <p className="text-on-surface-variant">{t('overview.subtitle')}</p>
      </motion.div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-8">
        {stats.map((stat, i) => {
          const Icon = stat.icon;
          return (
            <motion.div
              key={stat.title}
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.2 + i * 0.1 }}
              className="glass-panel ghost-border rounded-2xl p-6 relative overflow-hidden group"
            >
              <div className="absolute -right-6 -top-6 w-24 h-24 bg-surface-container-high rounded-full opacity-50 group-hover:scale-150 transition-transform duration-700 ease-out" />
              <div className="relative z-10 flex justify-between items-start mb-4">
                <div>
                  <p className="text-on-surface-variant font-sans text-sm font-medium mb-1">
                    {stat.title}
                  </p>
                  <h3 className="text-3xl font-bold font-sans">{stat.value}</h3>
                </div>
                <div
                  className={cn(
                    'w-12 h-12 rounded-xl bg-surface-container flex items-center justify-center ghost-border',
                    stat.color,
                  )}
                >
                  <Icon className="w-6 h-6" />
                </div>
              </div>
              <p className="relative z-10 text-sm text-on-surface-variant leading-relaxed">
                {loading ? t('history.loading') : stat.note}
              </p>
            </motion.div>
          );
        })}
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.5 }}
          className="lg:col-span-2 glass-panel ghost-border rounded-2xl p-6"
        >
          <div className="flex justify-between items-center mb-6">
            <h3 className="font-sans font-bold text-lg">{t('overview.discussionActivity')}</h3>
            <span className="text-[10px] font-bold tracking-[0.2em] uppercase text-on-surface-variant">
              {t('overview.last7days')}
            </span>
          </div>
          <div className="h-72 w-full">
            {loading ? (
              <div className="h-full flex items-center justify-center text-sm text-on-surface-variant">
                {t('history.loading')}
              </div>
            ) : hasActivity ? (
              <ResponsiveContainer width="100%" height="100%">
                <AreaChart data={activityData} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
                  <defs>
                    <linearGradient id="colorDiscussions" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="5%" stopColor="var(--color-primary)" stopOpacity={0.3} />
                      <stop offset="95%" stopColor="var(--color-primary)" stopOpacity={0} />
                    </linearGradient>
                  </defs>
                  <CartesianGrid strokeDasharray="3 3" stroke="var(--color-outline-variant)" vertical={false} />
                  <XAxis
                    dataKey="name"
                    stroke="var(--color-on-surface-variant)"
                    fontSize={12}
                    tickLine={false}
                    axisLine={false}
                  />
                  <YAxis
                    stroke="var(--color-on-surface-variant)"
                    fontSize={12}
                    tickLine={false}
                    axisLine={false}
                    allowDecimals={false}
                  />
                  <Tooltip
                    contentStyle={{
                      backgroundColor: 'var(--color-surface-container-high)',
                      borderColor: 'var(--color-outline-variant)',
                      borderRadius: '8px',
                      color: 'var(--color-on-surface)',
                    }}
                    itemStyle={{ color: 'var(--color-primary)' }}
                  />
                  <Area
                    type="monotone"
                    dataKey="discussions"
                    stroke="var(--color-primary)"
                    strokeWidth={3}
                    fillOpacity={1}
                    fill="url(#colorDiscussions)"
                  />
                </AreaChart>
              </ResponsiveContainer>
            ) : (
              <div className="h-full flex items-center justify-center text-center text-sm text-on-surface-variant">
                {t('overview.chartEmpty')}
              </div>
            )}
          </div>
        </motion.div>

        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.6 }}
          className="glass-panel ghost-border rounded-2xl p-6 flex flex-col"
        >
          <div className="flex justify-between items-center mb-6">
            <h3 className="font-sans font-bold text-lg">{t('overview.recentDiscussions')}</h3>
            <Link
              to="/history"
              className="text-primary hover:text-primary-fixed transition-colors text-sm font-medium"
            >
              {t('overview.viewAll')}
            </Link>
          </div>

          <div className="flex-1 space-y-4">
            {loading && recentDiscussions.length === 0 && (
              <div className="h-full flex items-center justify-center text-center text-sm text-on-surface-variant">
                {t('history.loading')}
              </div>
            )}

            {!loading && recentDiscussions.length === 0 && (
              <div className="h-full flex items-center justify-center text-center text-sm text-on-surface-variant">
                {t('overview.noRecentDiscussions')}
              </div>
            )}

            {recentDiscussions.map((discussion) => {
              const isRunning = discussion.status === 'running';
              const statusLabel = isRunning
                ? t('overview.live')
                : discussion.confidence ?? discussion.status;

              return (
                <Link
                  key={discussion.id}
                  to={`/discussion/${discussion.id}`}
                  className="block p-3 rounded-lg bg-surface-container-low ghost-border hover:bg-surface-container transition-colors"
                >
                  <p className="font-sans text-sm mb-2 line-clamp-2">{discussion.question}</p>
                  <div className="flex items-center justify-between gap-4">
                    <div className="flex items-center gap-2 min-w-0">
                      <span
                        className={cn(
                          'w-2 h-2 rounded-full shrink-0',
                          isRunning ? 'bg-primary animate-pulse neon-glow' : 'bg-green-500',
                        )}
                      />
                      <span className="text-[10px] font-bold tracking-widest text-on-surface-variant uppercase truncate">
                        {statusLabel}
                      </span>
                    </div>
                    <span className="font-mono text-xs text-on-surface-variant shrink-0">
                      {formatDisplayDate(discussion.created_at)}
                    </span>
                  </div>
                </Link>
              );
            })}
          </div>
        </motion.div>
      </div>
    </div>
  );
}
