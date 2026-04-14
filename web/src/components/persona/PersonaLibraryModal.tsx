import { useState } from 'react';
import { Plus, Search } from 'lucide-react';
import { Modal, Button } from '../ui';
import PersonaCard from './PersonaCard';
import PersonaDetailModal from './PersonaDetailModal';
import type { Persona } from '../../types/persona';

interface Props {
  isOpen: boolean;
  onClose: () => void;
  customPersonas: Persona[];
  onSave: (persona: Persona) => void;
  onDelete: (id: string) => void;
}

function createEmptyPersona(): Persona {
  return {
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
  };
}

export default function PersonaLibraryModal({
  isOpen,
  onClose,
  customPersonas,
  onSave,
  onDelete,
}: Props) {
  const [search, setSearch] = useState('');
  const [editing, setEditing] = useState<{ persona: Persona; isNew: boolean } | null>(null);

  const filtered = customPersonas.filter(
    (p) =>
      p.name.toLowerCase().includes(search.toLowerCase()) ||
      p.domain.toLowerCase().includes(search.toLowerCase()),
  );

  const handleCreate = () => {
    setEditing({ persona: createEmptyPersona(), isNew: true });
  };

  const handleSave = (persona: Persona) => {
    onSave(persona);
    setEditing(null);
  };

  return (
    <>
      <Modal isOpen={isOpen && !editing} onClose={onClose} title="Your Persona Library" size="lg">
        <div className="p-6">
          {/* Search + Create */}
          <div className="flex gap-3 mb-6">
            <div className="relative flex-1">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-white/40" />
              <input
                type="text"
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                placeholder="Search your personas..."
                className="w-full bg-[#1e2430] border border-white/10 rounded-xl py-2.5 pl-10 pr-4 text-sm text-white placeholder:text-white/30 focus:outline-none focus:border-[#00e5ff]/50 transition-colors"
              />
            </div>
            <Button onClick={handleCreate} size="md">
              <Plus className="w-4 h-4" /> Create New
            </Button>
          </div>

          {/* Grid or Empty State */}
          {filtered.length === 0 ? (
            <div className="text-center py-16">
              <div className="w-16 h-16 rounded-2xl bg-[#1e2430] flex items-center justify-center mx-auto mb-4">
                <Plus className="w-7 h-7 text-white/30" />
              </div>
              <h3 className="text-lg font-bold font-sans text-white/80 mb-2">
                {search ? 'No matching personas' : 'No custom personas yet'}
              </h3>
              <p className="text-sm text-white/40 font-serif italic mb-6">
                {search
                  ? 'Try a different search term.'
                  : 'Create your first custom expert to get started.'}
              </p>
              {!search && (
                <Button onClick={handleCreate}>Create Your First Expert</Button>
              )}
            </div>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              {filtered.map((p) => (
                <PersonaCard
                  key={p.id}
                  persona={p}
                  onClick={() => setEditing({ persona: p, isNew: false })}
                />
              ))}
            </div>
          )}
        </div>
      </Modal>

      {/* Detail/Edit Modal (stacks on top) */}
      {editing && (
        <PersonaDetailModal
          isOpen={true}
          persona={editing.persona}
          isNew={editing.isNew}
          onSave={handleSave}
          onDelete={(id) => {
            onDelete(id);
            setEditing(null);
          }}
          onClose={() => setEditing(null)}
        />
      )}
    </>
  );
}
