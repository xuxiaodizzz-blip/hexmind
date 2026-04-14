import { Activity, Zap } from 'lucide-react';
import { Badge } from '../ui';
import { cn } from '../../lib/utils';
import type { Persona } from '../../types/persona';

interface PersonaCardProps {
  persona: Persona;
  onClick?: () => void;
  className?: string;
}

export default function PersonaCard({ persona, onClick, className }: PersonaCardProps) {
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
            src={persona.avatar}
            alt={persona.name}
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
      </div>
      <h3 className="text-xl font-bold font-sans mb-3 leading-tight text-white/90 group-hover:text-white transition-colors">
        {persona.name}
      </h3>
      <p className="text-sm text-white/50 font-serif italic mb-8 flex-1 leading-relaxed">
        {persona.description}
      </p>
      <div className="flex items-center justify-between mt-auto">
        <div className="flex items-center gap-1.5 flex-wrap">
          {persona.tags.slice(0, 3).map((tag) => (
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
