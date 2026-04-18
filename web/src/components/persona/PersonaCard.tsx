import { Activity, Zap, Star } from 'lucide-react';
import { Badge } from '../ui';
import { cn } from '../../lib/utils';
import type { Persona } from '../../types/persona';
import { useLanguage } from '../../hooks/useLanguage';
import { resolveAvatarSrc } from '../../lib/avatar';

interface PersonaCardProps {
  persona: Persona;
  onClick?: () => void;
  className?: string;
  isFavorite?: boolean;
  onToggleFavorite?: () => void;
}

export default function PersonaCard({ persona, onClick, className, isFavorite, onToggleFavorite }: PersonaCardProps) {
  const { locale } = useLanguage();
  const name = locale === 'en' ? (persona.nameEn ?? persona.name) : persona.name;
  const description = locale === 'en' ? (persona.descriptionEn ?? persona.description) : persona.description;
  const tags = locale === 'en' ? (persona.tagsEn ?? persona.tags) : persona.tags;
  const avatarSrc = resolveAvatarSrc(persona.avatar, persona.id, name);
  return (
    <div
      onClick={onClick}
      className={cn(
        'bg-[#151a23] border border-white/5 rounded-2xl p-6 flex flex-col hover:border-white/10 transition-colors group',
        onClick && 'cursor-pointer',
        className,
      )}
    >
      <div className="flex items-start gap-4 mb-4">
        <div className="relative">
          <img
            src={avatarSrc}
            alt={name}
            className="w-16 h-16 rounded-2xl object-cover border border-white/10"
            referrerPolicy="no-referrer"
          />
          <div className="absolute -bottom-2 -right-2 w-6 h-6 bg-[#1e2430] rounded-full border border-white/10 flex items-center justify-center">
            <Zap className="w-3 h-3 text-white/70" />
          </div>
        </div>
        <div className="flex-1 pt-1">
          <Badge color={persona.domain}>{persona.domain}</Badge>
        </div>
        {onToggleFavorite && (
          <button
            type="button"
            onClick={(e) => {
              e.stopPropagation();
              onToggleFavorite();
            }}
            className="p-1.5 rounded-lg hover:bg-white/5 transition-colors"
            aria-label={isFavorite ? 'Remove from favorites' : 'Add to favorites'}
          >
            <Star
              className={cn(
                'w-5 h-5 transition-colors',
                isFavorite ? 'fill-[#ffd166] text-[#ffd166]' : 'text-white/30 hover:text-white/60',
              )}
            />
          </button>
        )}
      </div>
      <h3 className="text-xl font-bold font-sans mb-3 leading-tight text-white/90 group-hover:text-white transition-colors">
        {name}
      </h3>
      <p className="text-sm text-white/50 font-serif italic mb-8 flex-1 leading-relaxed">
        {description}
      </p>
      <div className="flex items-center justify-between mt-auto">
        <div className="flex items-center gap-1.5 flex-wrap">
          {tags.slice(0, 3).map((tag) => (
            <span
              key={tag}
              className="text-[10px] bg-white/5 text-white/60 px-2 py-1 rounded border border-white/5"
            >
              {tag}
            </span>
          ))}
        </div>
        {persona.sprints != null && persona.sprints > 0 && (
          <div className="flex items-center gap-1.5 text-xs text-white/40 font-medium shrink-0">
            <Activity className="w-3.5 h-3.5" />
            {persona.sprints.toLocaleString()} Sprints
          </div>
        )}
      </div>
    </div>
  );
}
