import { useState, useRef, useEffect } from 'react';
import { ChevronDown } from 'lucide-react';
import { cn } from '../../lib/utils';

interface Option {
  label: string;
  value: string;
  description?: string;
}

interface SelectProps {
  options: Option[];
  value: string;
  onChange: (value: string) => void;
  placeholder?: string;
  className?: string;
}

export default function Select({
  options,
  value,
  onChange,
  placeholder,
  className,
}: SelectProps) {
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const handler = (e: MouseEvent) => {
      if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false);
    };
    document.addEventListener('mousedown', handler);
    return () => document.removeEventListener('mousedown', handler);
  }, []);

  const selected = options.find((o) => o.value === value);

  return (
    <div ref={ref} className={cn('relative', className)}>
      <button
        type="button"
        onClick={() => setOpen(!open)}
        className="w-full bg-[#1e2430] border border-white/10 rounded-xl px-4 py-3 flex items-center justify-between hover:border-white/20 transition-colors"
      >
        <span className={cn('text-sm font-medium', selected ? 'text-white/90' : 'text-white/30')}>
          {selected?.label ?? placeholder ?? 'Select...'}
        </span>
        <ChevronDown
          className={cn('w-4 h-4 text-white/50 transition-transform', open && 'rotate-180')}
        />
      </button>
      {open && (
        <div className="absolute z-30 mt-1 w-full bg-[#1e2430] border border-white/10 rounded-xl shadow-xl overflow-hidden">
          {options.map((option) => (
            <button
              key={option.value}
              type="button"
              onClick={() => {
                onChange(option.value);
                setOpen(false);
              }}
              className={cn(
                'w-full text-left px-4 py-3 text-sm hover:bg-white/5 transition-colors',
                option.value === value ? 'text-[#00e5ff] bg-[#00e5ff]/5' : 'text-white/80',
              )}
            >
              <span className="font-medium">{option.label}</span>
              {option.description && (
                <span className="block text-[10px] text-white/40 mt-0.5">{option.description}</span>
              )}
            </button>
          ))}
        </div>
      )}
    </div>
  );
}
