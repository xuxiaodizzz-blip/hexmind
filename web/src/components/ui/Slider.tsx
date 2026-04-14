import { cn } from '../../lib/utils';

interface SliderProps {
  value: number;
  min: number;
  max: number;
  step?: number;
  onChange: (value: number) => void;
  minLabel?: string;
  maxLabel?: string;
  className?: string;
}

export default function Slider({
  value,
  min,
  max,
  step = 1,
  onChange,
  minLabel,
  maxLabel,
  className,
}: SliderProps) {
  const pct = ((value - min) / (max - min)) * 100;

  return (
    <div className={cn('space-y-2', className)}>
      <div className="relative h-1 bg-[#1e2430] rounded-full">
        <div
          className="absolute left-0 h-full bg-[#00e5ff] rounded-full shadow-[0_0_10px_rgba(0,229,255,0.5)]"
          style={{ width: `${pct}%` }}
        />
        <input
          type="range"
          min={min}
          max={max}
          step={step}
          value={value}
          onChange={(e) => onChange(Number(e.target.value))}
          className="absolute inset-0 w-full h-full opacity-0 cursor-pointer"
        />
        <div
          className="absolute top-1/2 w-3.5 h-3.5 bg-white rounded-full -translate-y-1/2 -translate-x-1/2 pointer-events-none shadow-md"
          style={{ left: `${pct}%` }}
        />
      </div>
      {(minLabel || maxLabel) && (
        <div className="flex justify-between text-[9px] font-bold tracking-widest text-white/30 uppercase">
          <span>{minLabel}</span>
          <span>{maxLabel}</span>
        </div>
      )}
    </div>
  );
}
