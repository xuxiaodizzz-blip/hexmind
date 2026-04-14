import { useState } from 'react';
import { motion } from 'motion/react';
import { Plus, Search } from 'lucide-react';
import { Tabs, Button } from '../components/ui';
import { PersonaCard, PersonaLibraryModal, PersonaDetailModal } from '../components/persona';
import { useLocalStorage } from '../hooks/useLocalStorage';
import { SYSTEM_PERSONAS, DOMAIN_TABS } from '../data/personas';
import type { Persona } from '../types/persona';

export default function Personas() {
  const [domain, setDomain] = useState('all');
  const [search, setSearch] = useState('');
  const [libraryOpen, setLibraryOpen] = useState(false);
  const [customPersonas, setCustomPersonas] = useLocalStorage<Persona[]>(
    'hexmind-custom-personas',
    [],
  );

  // For direct detail modal (clicking a card on the main page, or "Create Persona" button)
  const [detailState, setDetailState] = useState<{
    persona: Persona;
    isNew: boolean;
    readOnly: boolean;
  } | null>(null);

  const allPersonas = [...SYSTEM_PERSONAS, ...customPersonas];
  const filtered = allPersonas.filter((p) => {
    if (domain !== 'all' && p.domain !== domain) return false;
    if (search) {
      const q = search.toLowerCase();
      return (
        p.name.toLowerCase().includes(q) || p.description.toLowerCase().includes(q)
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

  const handleSavePersona = (persona: Persona) => {
    setCustomPersonas((prev) => {
      const idx = prev.findIndex((p) => p.id === persona.id);
      if (idx >= 0) {
        const next = [...prev];
        next[idx] = persona;
        return next;
      }
      return [...prev, persona];
    });
  };

  const handleDeletePersona = (id: string) => {
    setCustomPersonas((prev) => prev.filter((p) => p.id !== id));
  };

  const handleCardClick = (persona: Persona) => {
    setDetailState({
      persona,
      isNew: false,
      readOnly: !persona.isCustom,
    });
  };

  const handleCreateNew = () => {
    setDetailState({
      persona: {
        id: `custom-${Date.now()}`,
        name: '',
        role: '',
        domain: 'custom',
        description: '',
        prompt: '',
        avatar: '',
        tags: [],
        isPublic: false,
        isCustom: true,
      },
      isNew: true,
      readOnly: false,
    });
  };

  return (
    <div className="flex-1 overflow-y-auto no-scrollbar p-8 lg:p-12 z-10 w-full bg-[#0b0f17] text-white">
      <div className="max-w-6xl mx-auto">
        {/* Header */}
        <div className="flex flex-col md:flex-row md:items-end justify-between mb-10 gap-6">
          <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }}>
            <h1 className="text-4xl font-bold font-sans mb-2 tracking-tight">
              Personas Management
            </h1>
            <p className="text-white/50 font-serif italic text-lg">
              Orchestrate your fleet of digital specialists.
            </p>
          </motion.div>
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.1 }}
          >
            <Button onClick={handleCreateNew} variant="secondary" size="md">
              <Plus className="w-5 h-5" />
              Create Persona
            </Button>
          </motion.div>
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
              placeholder="Search archive..."
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
              <PersonaCard persona={p} onClick={() => handleCardClick(p)} />
            </motion.div>
          ))}

          {/* Add from Library Card */}
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
              Design Custom Expert
            </h3>
            <p className="text-sm text-white/50 font-serif italic px-4">
              Add a new dimension to your thought-pool.
            </p>
          </motion.div>
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
                Total Active Personas
              </p>
              <p className="text-4xl font-bold font-sans text-white">{totalActive}</p>
            </div>
            <div>
              <p className="text-[10px] font-bold tracking-[0.2em] text-white/40 uppercase mb-2">
                Most Active Domain
              </p>
              <p className="text-4xl font-bold font-sans text-[#b499ff] capitalize">
                {topDomain}
              </p>
            </div>
          </div>
          <div className="text-right max-w-sm">
            <p className="font-serif italic text-white/60 text-sm mb-2 leading-relaxed">
              "A multiplicity of perspectives is the only shield against the singularity
              of error."
            </p>
            <p className="text-[10px] font-bold tracking-widest text-[#00e5ff] uppercase">
              — Archive Protocol 04
            </p>
          </div>
        </motion.div>
      </div>

      {/* Library Modal (browse/edit custom personas) */}
      <PersonaLibraryModal
        isOpen={libraryOpen}
        onClose={() => setLibraryOpen(false)}
        customPersonas={customPersonas}
        onSave={handleSavePersona}
        onDelete={handleDeletePersona}
      />

      {/* Direct Detail Modal (view any persona / create new) */}
      {detailState && (
        <PersonaDetailModal
          isOpen={true}
          persona={detailState.persona}
          isNew={detailState.isNew}
          readOnly={detailState.readOnly}
          onSave={(p) => {
            handleSavePersona(p);
            setDetailState(null);
          }}
          onDelete={(id) => {
            handleDeletePersona(id);
            setDetailState(null);
          }}
          onClose={() => setDetailState(null)}
        />
      )}
    </div>
  );
}
