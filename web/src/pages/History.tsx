import { useEffect, useState } from 'react';
import { motion } from 'motion/react';
import { Link } from 'react-router-dom';
import { Search, Filter, Calendar } from 'lucide-react';
import { cn } from '../lib/utils';
import * as api from '../lib/api';
import { SYSTEM_PERSONAS } from '../data/personas';
import { useLanguage } from '../hooks/useLanguage';

export default function HistoryPage() {
  const { t, locale } = useLanguage();
  const [items, setItems] = useState<api.ArchiveSummary[]>([]);
  const [total, setTotal] = useState(0);
  const [query, setQuery] = useState('');
  const [offset, setOffset] = useState(0);
  const [loading, setLoading] = useState(true);
  const limit = 20;

  const fetchData = async () => {
    setLoading(true);
    try {
      const res = await api.getArchive({ query: query || undefined, limit, offset });
      setItems(res.items);
      setTotal(res.total);
    } catch {
      // If API is down, show empty
      setItems([]);
      setTotal(0);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
  }, [offset]);

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault();
    setOffset(0);
    fetchData();
  };

  const personaName = (pid: string) => {
    const p = SYSTEM_PERSONAS.find((x) => x.id === pid);
    if (!p) return pid;
    return locale === 'en' ? (p.nameEn ?? p.name) : p.name;
  };

  const totalPages = Math.max(1, Math.ceil(total / limit));
  const currentPage = Math.floor(offset / limit) + 1;
  return (
    <div className="flex-1 overflow-y-auto no-scrollbar p-8 lg:p-12 z-10 w-full bg-[#0b0f17] text-white">
      <div className="max-w-6xl mx-auto">
        {/* Header */}
        <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} className="mb-10">
          <h1 className="text-4xl font-bold font-sans mb-2 tracking-tight">{t('history.title')}</h1>
          <p className="text-white/50 font-serif italic text-lg">{t('history.subtitle')}</p>
        </motion.div>

        {/* Search & Filter Bar */}
        <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.1 }} className="flex flex-col md:flex-row gap-4 mb-8">
          <form onSubmit={handleSearch} className="relative flex-1">
            <Search className="absolute left-4 top-1/2 -translate-y-1/2 w-4 h-4 text-white/40" />
            <input
              type="text"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder={t('history.searchPlaceholder')}
              className="w-full bg-[#151a23] border border-transparent focus:border-white/20 rounded-xl py-3 pl-11 pr-4 text-sm text-white placeholder:text-white/30 focus:outline-none transition-colors"
            />
          </form>
          <div className="flex gap-3">
            <button className="flex items-center gap-2 px-4 py-3 bg-[#151a23] border border-white/5 rounded-xl text-sm text-white/70 hover:text-white hover:border-white/20 transition-colors">
              <Filter className="w-4 h-4" /> {t('history.filters')}
            </button>
            <button className="flex items-center gap-2 px-4 py-3 bg-[#151a23] border border-white/5 rounded-xl text-sm text-white/70 hover:text-white hover:border-white/20 transition-colors">
              <Calendar className="w-4 h-4" /> {t('history.dateRange')}
            </button>
          </div>
        </motion.div>

        {/* Status Tabs */}
        <div className="flex items-center gap-6 border-b border-white/10 mb-8">
          {[t('history.all'), t('history.running'), t('history.completed'), t('history.cancelled')].map((tab, i) => (
            <button
              key={tab}
              className={cn(
                'pb-3 text-sm font-bold tracking-widest uppercase transition-colors relative',
                i === 0 ? 'text-white' : 'text-white/40 hover:text-white/70'
              )}
            >
              {tab}
              {i === 0 && <div className="absolute bottom-0 left-0 w-full h-0.5 bg-white" />}
            </button>
          ))}
        </div>

        {/* Discussion Cards */}
        <div className="space-y-4">
          {loading && items.length === 0 && (
            <div className="text-center py-16 text-white/30 font-serif italic">{t('history.loading')}</div>
          )}
          {!loading && items.length === 0 && (
            <div className="text-center py-16 text-white/30 font-serif italic">{t('history.empty')}</div>
          )}
          {items.map((d, i) => (
            <motion.div
              key={d.id}
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.15 + i * 0.05 }}
            >
              <Link
                to={`/discussion/${d.id}`}
                className="block bg-[#151a23] border border-white/5 rounded-2xl p-6 hover:border-white/10 transition-colors"
              >
                <div className="flex items-start justify-between mb-4">
                  <h3 className="text-lg font-bold font-sans text-white/90 flex-1 pr-4">{d.question}</h3>
                  <div className="flex items-center gap-2 shrink-0">
                    <span
                      className={cn(
                        'w-2 h-2 rounded-full',
                        d.status === 'running' && 'bg-[#00e5ff] animate-pulse neon-glow',
                        d.status === 'converged' && 'bg-green-500',
                        d.status === 'cancelled' && 'bg-white/20',
                        !['running', 'converged', 'cancelled'].includes(d.status) && 'bg-yellow-400'
                      )}
                    />
                    <span className="text-[10px] font-bold tracking-widest text-white/50 uppercase">{d.status}</span>
                  </div>
                </div>

                <div className="flex flex-wrap items-center gap-x-6 gap-y-2 text-sm text-white/50">
                  <span>
                    👤 {d.personas.slice(0, 2).map(personaName).join(', ')}
                    {d.personas.length > 2 && ` +${d.personas.length - 2}`}
                  </span>
                  {d.confidence && <span>📊 {d.confidence}</span>}
                  <span>📅 {d.created_at.slice(0, 10)}</span>
                </div>

                {d.verdict && (
                  <p className="mt-3 text-sm text-white/40 font-serif italic line-clamp-1">
                    → {d.verdict}
                  </p>
                )}
              </Link>
            </motion.div>
          ))}
        </div>

        {/* Pagination */}
        {total > limit && (
          <div className="flex justify-center mt-10">
            <div className="flex items-center gap-2">
              <button
                onClick={() => setOffset(Math.max(0, offset - limit))}
                disabled={offset === 0}
                className="px-4 py-2 bg-[#151a23] border border-white/5 rounded-lg text-sm text-white/50 hover:text-white transition-colors disabled:opacity-30 disabled:cursor-not-allowed"
              >
                {t('history.prev')}
              </button>
              <span className="text-sm text-white/50 px-4">{t('history.page', { current: String(currentPage), total: String(totalPages) })}</span>
              <button
                onClick={() => setOffset(offset + limit)}
                disabled={offset + limit >= total}
                className="px-4 py-2 bg-[#151a23] border border-white/5 rounded-lg text-sm text-white/50 hover:text-white transition-colors disabled:opacity-30 disabled:cursor-not-allowed"
              >
                {t('history.next')}
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
