import { forwardRef, type ButtonHTMLAttributes, type ReactNode } from 'react';
import { cn } from '../../lib/utils';

const variants = {
  primary:
    'bg-[#00e5ff] hover:bg-[#00cce6] text-black font-bold shadow-[0_0_20px_rgba(0,229,255,0.2)]',
  secondary:
    'bg-[#151a23] border border-white/10 text-white hover:bg-white/5 font-bold',
  ghost: 'bg-transparent text-white/50 hover:text-white hover:bg-white/[0.03]',
  danger:
    'bg-rose-500/10 text-rose-400 border border-rose-500/20 hover:bg-rose-500/20 font-bold',
};

const sizes = {
  sm: 'h-8 px-3 text-xs gap-1.5 rounded-lg',
  md: 'h-10 px-5 text-sm gap-2 rounded-xl',
  lg: 'h-12 px-6 text-base gap-2 rounded-xl',
};

interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: keyof typeof variants;
  size?: keyof typeof sizes;
  children: ReactNode;
}

const Button = forwardRef<HTMLButtonElement, ButtonProps>(
  ({ className, variant = 'primary', size = 'md', children, ...props }, ref) => (
    <button
      ref={ref}
      className={cn(
        'inline-flex items-center justify-center transition-colors disabled:opacity-30 disabled:cursor-not-allowed',
        variants[variant],
        sizes[size],
        className,
      )}
      {...props}
    >
      {children}
    </button>
  ),
);
Button.displayName = 'Button';
export default Button;
