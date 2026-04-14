import { useState } from 'react';
import { Modal, Button, Select } from '../ui';
import type { Persona } from '../../types/persona';

const domainOptions = [
  { label: 'Tech', value: 'tech' },
  { label: 'Business', value: 'business' },
  { label: 'Medical', value: 'medical' },
  { label: 'Creative', value: 'creative' },
  { label: 'Custom', value: 'custom' },
];

interface Props {
  isOpen: boolean;
  persona: Persona;
  isNew: boolean;
  readOnly?: boolean;
  onSave: (persona: Persona) => void;
  onDelete: (id: string) => void;
  onClose: () => void;
}

export default function PersonaDetailModal({
  isOpen,
  persona,
  isNew,
  readOnly,
  onSave,
  onDelete,
  onClose,
}: Props) {
  const [form, setForm] = useState<Persona>({ ...persona });

  const update = <K extends keyof Persona>(key: K, value: Persona[K]) => {
    setForm((prev) => ({ ...prev, [key]: value }));
  };

  const handleSave = () => {
    if (!form.name.trim() || !form.prompt.trim()) return;
    if (!form.avatar) {
      form.avatar = `https://picsum.photos/seed/${form.id}/150/150`;
    }
    onSave({ ...form, isCustom: true });
  };

  return (
    <Modal
      isOpen={isOpen}
      onClose={onClose}
      title={readOnly ? persona.name : isNew ? 'Create Persona' : 'Edit Persona'}
      size="md"
    >
      <div className="p-6 space-y-5">
        {/* Name */}
        <div>
          <label className="block text-[10px] font-bold tracking-[0.15em] text-white/50 uppercase mb-2">
            Name
          </label>
          <input
            type="text"
            value={form.name}
            onChange={(e) => update('name', e.target.value)}
            placeholder="e.g. The Pragmatic Auditor"
            disabled={readOnly}
            className="w-full bg-[#1e2430] border border-white/10 rounded-xl px-4 py-3 text-sm text-white placeholder:text-white/30 focus:outline-none focus:border-[#00e5ff]/50 transition-colors disabled:opacity-60 disabled:cursor-not-allowed"
          />
        </div>

        {/* Domain */}
        {!readOnly ? (
          <div>
            <label className="block text-[10px] font-bold tracking-[0.15em] text-white/50 uppercase mb-2">
              Domain
            </label>
            <Select
              options={domainOptions}
              value={form.domain}
              onChange={(v) => update('domain', v as Persona['domain'])}
            />
          </div>
        ) : (
          <div>
            <label className="block text-[10px] font-bold tracking-[0.15em] text-white/50 uppercase mb-2">
              Domain
            </label>
            <p className="text-sm text-white/80 capitalize">{form.domain}</p>
          </div>
        )}

        {/* Description */}
        <div>
          <label className="block text-[10px] font-bold tracking-[0.15em] text-white/50 uppercase mb-2">
            Description
          </label>
          <input
            type="text"
            value={form.description}
            onChange={(e) => update('description', e.target.value)}
            placeholder="One-line description of this persona's expertise"
            disabled={readOnly}
            className="w-full bg-[#1e2430] border border-white/10 rounded-xl px-4 py-3 text-sm text-white placeholder:text-white/30 focus:outline-none focus:border-[#00e5ff]/50 transition-colors disabled:opacity-60 disabled:cursor-not-allowed"
          />
        </div>

        {/* System Prompt */}
        <div>
          <label className="block text-[10px] font-bold tracking-[0.15em] text-white/50 uppercase mb-2">
            System Prompt <span className="text-[#00e5ff]">*</span>
          </label>
          <textarea
            value={form.prompt}
            onChange={(e) => update('prompt', e.target.value)}
            placeholder="Define this persona's behavior, expertise, and communication style..."
            rows={8}
            disabled={readOnly}
            className="w-full bg-[#1e2430] border border-white/10 rounded-xl px-4 py-3 text-sm text-white placeholder:text-white/30 focus:outline-none focus:border-[#00e5ff]/50 transition-colors resize-none font-mono leading-relaxed disabled:opacity-60 disabled:cursor-not-allowed"
          />
        </div>

        {/* Tags */}
        <div>
          <label className="block text-[10px] font-bold tracking-[0.15em] text-white/50 uppercase mb-2">
            Tags (comma separated)
          </label>
          <input
            type="text"
            value={form.tags.join(', ')}
            onChange={(e) =>
              update(
                'tags',
                e.target.value
                  .split(',')
                  .map((t) => t.trim())
                  .filter(Boolean),
              )
            }
            placeholder="e.g. Finance, Risk, Compliance"
            disabled={readOnly}
            className="w-full bg-[#1e2430] border border-white/10 rounded-xl px-4 py-3 text-sm text-white placeholder:text-white/30 focus:outline-none focus:border-[#00e5ff]/50 transition-colors disabled:opacity-60 disabled:cursor-not-allowed"
          />
        </div>

        {/* Public toggle */}
        {!readOnly && (
          <div className="flex items-center justify-between p-4 bg-[#1e2430] rounded-xl border border-white/5">
            <div>
              <p className="font-sans font-medium text-sm text-white">Make Public</p>
              <p className="text-xs text-white/40">
                Allow other users to discover and use this persona
              </p>
            </div>
            <button
              type="button"
              onClick={() => update('isPublic', !form.isPublic)}
              className={`w-11 h-6 rounded-full transition-colors relative ${form.isPublic ? 'bg-[#00e5ff]' : 'bg-[#1e2430] border border-white/20'}`}
            >
              <div
                className={`w-4 h-4 rounded-full bg-white absolute top-1 transition-transform ${form.isPublic ? 'translate-x-6' : 'translate-x-1'}`}
              />
            </button>
          </div>
        )}

        {/* Actions */}
        <div className="flex items-center justify-between pt-4 border-t border-white/5">
          {!isNew && !readOnly ? (
            <Button
              variant="danger"
              size="sm"
              onClick={() => {
                onDelete(persona.id);
                onClose();
              }}
            >
              Delete
            </Button>
          ) : (
            <div />
          )}
          <div className="flex gap-3">
            <Button variant="secondary" size="md" onClick={onClose}>
              {readOnly ? 'Close' : 'Cancel'}
            </Button>
            {!readOnly && (
              <Button
                size="md"
                onClick={handleSave}
                disabled={!form.name.trim() || !form.prompt.trim()}
              >
                {isNew ? 'Create' : 'Save'}
              </Button>
            )}
          </div>
        </div>
      </div>
    </Modal>
  );
}
