import { cn } from '../../lib/utils';

interface Tab {
  label: string;
  value: string;
}

interface TabsProps {
  tabs: Tab[];
  value: string;
  onChange: (value: string) => void;
  className?: string;
}

export default function Tabs({ tabs, value, onChange, className }: TabsProps) {
  return (
    <div className={cn('flex items-center gap-6 border-b border-white/10', className)}>
      {tabs.map((tab) => (
        <button
          key={tab.value}
          onClick={() => onChange(tab.value)}
          className={cn(
            'pb-3 text-sm font-bold tracking-widest uppercase transition-colors relative',
            value === tab.value ? 'text-white' : 'text-white/40 hover:text-white/70',
          )}
        >
          {tab.label}
          {value === tab.value && (
            <div className="absolute bottom-0 left-0 w-full h-0.5 bg-white" />
          )}
        </button>
      ))}
    </div>
  );
}
