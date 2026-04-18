import { useState } from 'react';
import { Modal, Button, Select } from '../ui';
import type { Persona } from '../../types/persona';
import { useLanguage } from '../../hooks/useLanguage';

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
  const { locale, t } = useLanguage();
  const displayName = locale === 'en' ? (persona.nameEn ?? persona.name) : persona.name;

  const update = <K extends keyof Persona>(key: K, value: Persona[K]) => {
    setForm((prev) => ({ ...prev, [key]: value }));
  };

  const handleSave = () => {
    if (!form.name.trim() || !form.prompt.trim()) return;
    onSave({ ...form, isCustom: true });
  };

  return (
    <Modal
      isOpen={isOpen}
      onClose={onClose}
      title={readOnly ? displayName : isNew ? t('personaModal.create' as any) : t('personaModal.editPersona' as any)}
      size="md"
    >
      <div className="p-6 space-y-5">
        {/* Name */}
        <div>
          <label className="block text-[10px] font-bold tracking-[0.15em] text-white/50 uppercase mb-2">
            {t('personaModal.name' as any)}
          </label>
          <input
            type="text"
            value={form.name}
            onChange={(e) => update('name', e.target.value)}
            placeholder={t('personaModal.namePlaceholder' as any)}
            disabled={readOnly}
            className="w-full bg-[#1e2430] border border-white/10 rounded-xl px-4 py-3 text-sm text-white placeholder:text-white/30 focus:outline-none focus:border-[#00e5ff]/50 transition-colors disabled:opacity-60 disabled:cursor-not-allowed"
          />
        </div>

        {/* Domain */}
        {!readOnly ? (
          <div>
            <label className="block text-[10px] font-bold tracking-[0.15em] text-white/50 uppercase mb-2">
              {t('personaModal.domain' as any)}
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
              {t('personaModal.domain' as any)}
            </label>
            <p className="text-sm text-white/80 capitalize">{form.domain}</p>
          </div>
        )}

        {/* Description */}
        <div>
          <label className="block text-[10px] font-bold tracking-[0.15em] text-white/50 uppercase mb-2">
            {t('personaModal.description' as any)}
          </label>
          <input
            type="text"
            value={form.description}
            onChange={(e) => update('description', e.target.value)}
            placeholder={t('personaModal.descPlaceholder' as any)}
            disabled={readOnly}
            className="w-full bg-[#1e2430] border border-white/10 rounded-xl px-4 py-3 text-sm text-white placeholder:text-white/30 focus:outline-none focus:border-[#00e5ff]/50 transition-colors disabled:opacity-60 disabled:cursor-not-allowed"
          />
        </div>

        {/* System Prompt */}
        <div>
          <label className="block text-[10px] font-bold tracking-[0.15em] text-white/50 uppercase mb-2">
            {t('personaModal.systemPrompt' as any)} <span className="text-[#00e5ff]">*</span>
          </label>
          <textarea
            value={form.prompt}
            onChange={(e) => update('prompt', e.target.value)}
            placeholder={t('personaModal.promptPlaceholder' as any)}
            rows={8}
            disabled={readOnly}
            className="w-full bg-[#1e2430] border border-white/10 rounded-xl px-4 py-3 text-sm text-white placeholder:text-white/30 focus:outline-none focus:border-[#00e5ff]/50 transition-colors resize-none font-mono leading-relaxed disabled:opacity-60 disabled:cursor-not-allowed"
          />
        </div>

        {/* Tags */}
        <div>
          <label className="block text-[10px] font-bold tracking-[0.15em] text-white/50 uppercase mb-2">
            {t('personaModal.tags' as any)}
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
            placeholder={t('personaModal.tagsPlaceholder' as any)}
            disabled={readOnly}
            className="w-full bg-[#1e2430] border border-white/10 rounded-xl px-4 py-3 text-sm text-white placeholder:text-white/30 focus:outline-none focus:border-[#00e5ff]/50 transition-colors disabled:opacity-60 disabled:cursor-not-allowed"
          />
        </div>

        {/* Public toggle */}
        {!readOnly && (
          <div className="flex items-center justify-between p-4 bg-[#1e2430] rounded-xl border border-white/5">
            <div>
              <p className="font-sans font-medium text-sm text-white">{t('personaModal.makePublic' as any)}</p>
              <p className="text-xs text-white/40">
                {t('personaModal.makePublicDesc' as any)}
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
              {t('personaModal.delete' as any)}
            </Button>
          ) : (
            <div />
          )}
          <div className="flex gap-3">
            <Button variant="secondary" size="md" onClick={onClose}>
              {readOnly ? t('personaModal.close' as any) : t('personaModal.cancel' as any)}
            </Button>
            {!readOnly && (
              <Button
                size="md"
                onClick={handleSave}
                disabled={!form.name.trim() || !form.prompt.trim()}
              >
                {isNew ? t('personaModal.create' as any) : t('personaModal.save' as any)}
              </Button>
            )}
          </div>
        </div>
      </div>
    </Modal>
  );
}
