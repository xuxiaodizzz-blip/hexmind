import { motion } from 'motion/react';
import { MessageSquare, Palette, Sun, Moon, Monitor, Minus, Plus, ChevronDown } from 'lucide-react';
import { useTheme } from '../hooks/useTheme';
import { cn } from '../lib/utils';

type ThemeOption = 'light' | 'dark' | 'system';

const themeOptions: { value: ThemeOption; label: string; icon: typeof Sun }[] = [
  { value: 'light', label: 'Light', icon: Sun },
  { value: 'dark', label: 'Dark', icon: Moon },
  { value: 'system', label: 'System', icon: Monitor },
];

export default function Settings() {
  const { theme, setTheme } = useTheme();

  return (
    <div className="flex-1 overflow-y-auto no-scrollbar p-8 lg:p-12 z-10 w-full">
      <div className="max-w-4xl mx-auto">
        {/* Section 1: Discussion Defaults */}
        <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} className="mb-12">
          <div className="flex items-center gap-4 mb-6">
            <div className="w-10 h-10 rounded-lg bg-[#1a202c] flex items-center justify-center">
              <MessageSquare className="w-5 h-5 text-[#c3f5ff]" />
            </div>
            <h2 className="text-2xl font-serif italic text-white">Discussion Defaults</h2>
          </div>

          <div className="bg-[#151a23] rounded-2xl p-8 border border-white/5 shadow-lg">
            <div className="grid grid-cols-1 md:grid-cols-3 gap-12">
              <div>
                <h3 className="text-[10px] font-sans font-bold text-white/50 tracking-[0.15em] uppercase mb-6">Token Budget</h3>
                <div className="h-1 bg-[#1e2430] rounded-full overflow-hidden mb-3">
                  <div className="h-full bg-[#c3f5ff] w-1/4 rounded-full shadow-[0_0_10px_rgba(195,245,255,0.5)]" />
                </div>
                <div className="flex justify-between items-center text-[9px] font-bold tracking-wider">
                  <span className="text-white/50">128K</span>
                  <span className="text-white">512K MAX</span>
                </div>
              </div>

              <div>
                <h3 className="text-[10px] font-sans font-bold text-white/50 tracking-[0.15em] uppercase mb-4">Time Limit</h3>
                <div className="flex items-baseline gap-2 mb-4">
                  <span className="text-3xl font-bold font-sans text-white">15</span>
                  <span className="font-serif italic text-white/50 text-lg">minutes</span>
                </div>
                <div className="relative h-1 bg-[#1e2430] rounded-full flex items-center">
                  <div className="absolute left-0 h-full bg-[#3b494c] w-1/2 rounded-full" />
                  <div className="absolute left-1/2 w-3.5 h-3.5 bg-[#c3f5ff] rounded-full shadow-[0_0_10px_rgba(195,245,255,0.8)] -translate-x-1/2 cursor-pointer" />
                </div>
              </div>

              <div>
                <h3 className="text-[10px] font-sans font-bold text-white/50 tracking-[0.15em] uppercase mb-6">Synthesis Rounds</h3>
                <div className="bg-[#1e2430] rounded-xl p-2 flex items-center justify-between border border-white/5">
                  <button className="w-8 h-8 flex items-center justify-center text-white/50 hover:text-white transition-colors">
                    <Minus className="w-4 h-4" />
                  </button>
                  <span className="font-sans font-bold text-lg text-white">04</span>
                  <button className="w-8 h-8 flex items-center justify-center text-white/50 hover:text-white transition-colors">
                    <Plus className="w-4 h-4" />
                  </button>
                </div>
              </div>
            </div>
          </div>
        </motion.div>

        {/* Section 2: UI Settings */}
        <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.1 }} className="mb-12">
          <div className="flex items-center gap-4 mb-6">
            <div className="w-10 h-10 rounded-lg bg-[#1a202c] flex items-center justify-center">
              <Palette className="w-5 h-5 text-[#c3f5ff]" />
            </div>
            <h2 className="text-2xl font-serif italic text-white">UI Settings</h2>
          </div>

          <div className="bg-[#151a23] rounded-2xl p-8 border border-white/5 shadow-lg">
            <div className="flex items-center justify-between mb-10">
              <div>
                <h3 className="font-sans font-bold text-white mb-1">Language Interface</h3>
                <p className="font-serif italic text-white/50 text-sm">Select the lexicon of the Scriptorium</p>
              </div>
              <div className="bg-[#1e2430] border border-white/10 rounded-lg px-4 py-2.5 flex items-center gap-3 cursor-pointer hover:border-white/20 transition-colors">
                <span className="font-sans text-sm text-white/80">English (Oxford)</span>
                <ChevronDown className="w-4 h-4 text-white/50" />
              </div>
            </div>

            <div>
              <h3 className="text-[10px] font-sans font-bold text-white/50 tracking-[0.15em] uppercase mb-4">Luminance Mode</h3>
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                {themeOptions.map((opt) => {
                  const Icon = opt.icon;
                  const isActive = theme === opt.value;
                  return (
                    <button
                      key={opt.value}
                      onClick={() => setTheme(opt.value)}
                      className={cn(
                        'rounded-xl p-4 flex items-center gap-3 cursor-pointer relative overflow-hidden transition-colors text-left',
                        isActive
                          ? 'bg-[#1e2430] border border-[#c3f5ff]/50 shadow-[0_0_15px_rgba(195,245,255,0.05)]'
                          : 'bg-[#1e2430] border border-transparent hover:border-white/10',
                      )}
                    >
                      {isActive && <div className="absolute inset-0 bg-[#c3f5ff]/5" />}
                      <Icon className={cn('w-5 h-5 relative z-10', isActive ? 'text-[#c3f5ff]' : 'text-white/50')} />
                      <span className={cn('font-sans font-medium text-sm relative z-10', isActive ? 'text-white' : 'text-white/80')}>
                        {opt.label}
                      </span>
                    </button>
                  );
                })}
              </div>
            </div>
          </div>
        </motion.div>
      </div>
    </div>
  );
}
