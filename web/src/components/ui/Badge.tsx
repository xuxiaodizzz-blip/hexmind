import { cn } from '../../lib/utils';

const colorMap: Record<string, string> = {
  tech: 'bg-indigo-500/20 text-indigo-300',
  business: 'bg-amber-500/20 text-amber-300',
  medical: 'bg-rose-500/20 text-rose-300',
  creative: 'bg-teal-500/20 text-teal-300',
  custom: 'bg-purple-500/20 text-purple-300',
  default: 'bg-white/5 text-white/60',
};

interface BadgeProps {
  children: React.ReactNode;
  color?: string;
  className?: string;
}

export default function Badge({ children, color = 'default', className }: BadgeProps) {
  return (
    <span
      className={cn(
        'inline-flex items-center text-[9px] font-bold tracking-wider px-2 py-0.5 rounded uppercase',
        colorMap[color] ?? colorMap.default,
        className,
      )}
    >
      {children}
    </span>
  );
}
