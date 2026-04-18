import { useState } from 'react';
import { motion } from 'motion/react';
import { Search, Star } from 'lucide-react';
import { Tabs } from '../components/ui';
import { PersonaCard, PersonaDetailModal } from '../components/persona';
import { useLocalStorage } from '../hooks/useLocalStorage';
import { SYSTEM_PERSONAS, DOMAIN_TABS } from '../data/personas';
import type { Persona } from '../types/persona';
import { useLanguage } from '../hooks/useLanguage';

// ─────────────────────────────────────────────────────────────────────────────
// MVP NOTE — User-created personas are temporarily DISABLED.
//
// Why: The full "create + prompt-expert + save + edit" feature is a v2 scope
//   item (meta-prompt generation, visual editor, server-side CRUD).
//   See docs/design/persona-creator-v2.md for the planned design.
//
// What's still active in MVP:
//   - Browsing the system persona library (SYSTEM_PERSONAS)
//   - Per-user "Favorites" stored in localStorage
//   - Read-only persona detail modal
//
// To re-enable user-created personas: search for "PERSONA_CREATOR_V2" and
//   restore the commented blocks; restore "PersonaLibraryModal" import.
// ─────────────────────────────────────────────────────────────────────────────

export default function Personas() {
  const { t } = useLanguage();
  // Default tab is 'tech' (a content tab). 'favorites' is selectable but starts empty.
  const [domain, setDomain] = useState('tech');
  const [search, setSearch] = useState('');

  // Per-user favorites (client-only, no server sync). Stores persona IDs.
  const [favoriteIds, setFavoriteIds] = useLocalStorage<string[]>(
    'hexmind-favorite-personas',
    [],
  );
  const favoriteSet = new Set(favoriteIds);

  const toggleFavorite = (id: string) => {
    setFavoriteIds((prev) =>
      prev.includes(id) ? prev.filter((x) => x !== id) : [...prev, id],
    );
  };

  // PERSONA_CREATOR_V2 (disabled for MVP): user-created personas
  // const [customPersonas, setCustomPersonas] = useLocalStorage<Persona[]>(
  //   'hexmind-custom-personas',
  //   [],
  // );
  // const [libraryOpen, setLibraryOpen] = useState(false);

  // For read-only detail modal (clicking a card opens it)
  const [detailState, setDetailState] = useState<{
    persona: Persona;
    isNew: boolean;
    readOnly: boolean;
  } | null>(null);

  // MVP: only system personas are shown. Custom personas re-enabled in v2.
  const allPersonas = SYSTEM_PERSONAS;
  const filtered = allPersonas.filter((p) => {
    if (domain === 'favorites') {
      if (!favoriteSet.has(p.id)) return false;
    } else if (p.domain !== domain) {
      return false;
    }
    if (search) {
      const q = search.toLowerCase();
      return (
        p.name.toLowerCase().includes(q) || p.description.toLowerCase().includes(q) ||
        (p.nameEn?.toLowerCase().includes(q) ?? false) || (p.descriptionEn?.toLowerCase().includes(q) ?? false)
      );
    }
    return true;
  });

  // Computed stats
  const totalActive = allPersonas.length;
  const domainCounts = allPersonas.reduce(
    (acc, p) => {
      acc[p.domain] = (acc[p.domain] || 0) + 1;
      return acc;
    },
    {} as Record<string, number>,
  );
  const topDomain =
    Object.entries(domainCounts).sort(([, a], [, b]) => b - a)[0]?.[0] ?? 'tech';

  // PERSONA_CREATOR_V2 (disabled): handlers retained as comments for v2 reactivation
  // const handleSavePersona = (persona: Persona) => { ... };
  // const handleDeletePersona = (id: string) => { ... };
  // const handleCreateNew = () => { ... };

  const handleCardClick = (persona: Persona) => {
    setDetailState({
      persona,
      isNew: false,
      readOnly: true, // MVP: all personas are read-only
    });
  };

  return (
    <div className="flex-1 overflow-y-auto no-scrollbar p-8 lg:p-12 z-10 w-full bg-[#0b0f17] text-white">
      <div className="max-w-6xl mx-auto">
        {/* Header */}
        <div className="flex flex-col md:flex-row md:items-end justify-between mb-10 gap-6">
          <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }}>
            <h1 className="text-4xl font-bold font-sans mb-2 tracking-tight">
              {t('personas.title')}
            </h1>
            <p className="text-white/50 font-serif italic text-lg">
              {t('personas.subtitle')}
            </p>
          </motion.div>
          {/* PERSONA_CREATOR_V2 (disabled for MVP): Create Persona button
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.1 }}
          >
            <Button onClick={handleCreateNew} variant="secondary" size="md">
              <Plus className="w-5 h-5" />
              {t('personas.createPersona')}
            </Button>
          </motion.div>
          */}
        </div>

        {/* Tabs & Search */}
        <div className="flex flex-col md:flex-row justify-between items-start md:items-center mb-8 gap-6">
          <Tabs tabs={DOMAIN_TABS} value={domain} onChange={setDomain} className="w-full md:w-auto" />
          <div className="relative w-full md:w-72">
            <Search className="absolute left-4 top-1/2 -translate-y-1/2 w-4 h-4 text-white/40" />
            <input
              type="text"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder={t('personas.searchPlaceholder')}
              className="w-full bg-[#151a23] border border-transparent focus:border-white/20 rounded-xl py-2.5 pl-11 pr-4 text-sm text-white placeholder:text-white/30 focus:outline-none transition-colors"
            />
          </div>
        </div>

        {/* Grid */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-6 mb-12">
          {filtered.map((p, i) => (
            <motion.div
              key={p.id}
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: i * 0.05 }}
            >
              <PersonaCard
                persona={p}
                onClick={() => handleCardClick(p)}
                isFavorite={favoriteSet.has(p.id)}
                onToggleFavorite={() => toggleFavorite(p.id)}
              />
            </motion.div>
          ))}

          {/* Favorites empty state */}
          {domain === 'favorites' && filtered.length === 0 && (
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              className="col-span-full border-2 border-dashed border-white/10 rounded-2xl p-12 flex flex-col items-center justify-center text-center"
            >
              <div className="w-14 h-14 rounded-2xl bg-[#2a3441] flex items-center justify-center mb-6">
                <Star className="w-6 h-6 text-white/70" />
              </div>
              <h3 className="text-lg font-bold font-sans mb-2 text-white/90">
                {t('personas.favoritesEmptyTitle')}
              </h3>
              <p className="text-sm text-white/50 font-serif italic px-4 max-w-md">
                {t('personas.favoritesEmptyDesc')}
              </p>
            </motion.div>
          )}

          {/* PERSONA_CREATOR_V2 (disabled for MVP): "Add from Library" card
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: filtered.length * 0.05 }}
            onClick={() => setLibraryOpen(true)}
            className="border-2 border-dashed border-white/10 rounded-2xl p-6 flex flex-col items-center justify-center text-center hover:bg-white/[0.02] hover:border-white/20 transition-colors cursor-pointer min-h-[280px]"
          >
            <div className="w-14 h-14 rounded-2xl bg-[#2a3441] flex items-center justify-center mb-6">
              <Plus className="w-6 h-6 text-white/70" />
            </div>
            <h3 className="text-lg font-bold font-sans mb-2 text-white/90">
              {t('personas.designCustom')}
            </h3>
            <p className="text-sm text-white/50 font-serif italic px-4">
              {t('personas.designCustomDesc')}
            </p>
          </motion.div>
          */}
        </div>

        {/* Bottom Stats Bar */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.5 }}
          className="bg-[#151a23] border border-white/5 rounded-2xl p-8 flex flex-col md:flex-row items-center justify-between gap-8"
        >
          <div className="flex items-center gap-16">
            <div>
              <p className="text-[10px] font-bold tracking-[0.2em] text-white/40 uppercase mb-2">
                {t('personas.totalActive')}
              </p>
              <p className="text-4xl font-bold font-sans text-white">{totalActive}</p>
            </div>
            <div>
              <p className="text-[10px] font-bold tracking-[0.2em] text-white/40 uppercase mb-2">
                {t('personas.mostActiveDomain')}
              </p>
              <p className="text-4xl font-bold font-sans text-[#b499ff] capitalize">
                {topDomain}
              </p>
            </div>
          </div>
          <div className="text-right max-w-sm">
            <p className="font-serif italic text-white/60 text-sm mb-2 leading-relaxed">
              {t('personas.quote')}
            </p>
            <p className="text-[10px] font-bold tracking-widest text-[#00e5ff] uppercase">
              {t('personas.quoteSource')}
            </p>
          </div>
        </motion.div>
      </div>

      {/* PERSONA_CREATOR_V2 (disabled for MVP): Library modal
      <PersonaLibraryModal
        isOpen={libraryOpen}
        onClose={() => setLibraryOpen(false)}
        customPersonas={customPersonas}
        onSave={handleSavePersona}
        onDelete={handleDeletePersona}
      />
      */}

      {/* Read-only Detail Modal */}
      {detailState && (
        <PersonaDetailModal
          isOpen={true}
          persona={detailState.persona}
          isNew={detailState.isNew}
          readOnly={detailState.readOnly}
          onSave={() => setDetailState(null)}
          onDelete={() => setDetailState(null)}
          onClose={() => setDetailState(null)}
        />
      )}
    </div>
  );
}
