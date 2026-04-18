import { Link, useLocation } from 'react-router-dom';
import { motion } from 'motion/react';
import { UserButton } from '@clerk/clerk-react';
import {
  LayoutDashboard,
  MessageSquare,
  History,
  Users,
  FolderOpen,
  UsersRound,
  Settings as SettingsIcon,
  // PRICING_V2 (disabled for MVP): CreditCard,
  Plus,
  Hexagon,
} from 'lucide-react';
import { cn } from '../../lib/utils';
import { useLanguage } from '../../hooks/useLanguage';
import type { TranslationKey } from '../../i18n/en';
import { LOCAL_ONLY_MODE, CLERK_ENABLED } from '../../lib/runtime';

const navItems: { nameKey: TranslationKey; path: string; icon: typeof LayoutDashboard; highlight?: boolean }[] = [
  { nameKey: 'sidebar.dashboard', path: '/', icon: LayoutDashboard },
  { nameKey: 'sidebar.newDiscussion', path: '/new', icon: MessageSquare, highlight: true },
  { nameKey: 'sidebar.history', path: '/history', icon: History },
  { nameKey: 'sidebar.personas', path: '/personas', icon: Users },
  { nameKey: 'sidebar.assets', path: '/assets', icon: FolderOpen },
  { nameKey: 'sidebar.teams', path: '/teams', icon: UsersRound },
  // PRICING_V2 (disabled for MVP): Billing entry hidden until pricing model is set.
  // { nameKey: 'sidebar.billing', path: '/billing', icon: CreditCard },
  { nameKey: 'sidebar.settings', path: '/settings', icon: SettingsIcon },
];

export default function Sidebar() {
  const location = useLocation();
  const { t, locale } = useLanguage();

  return (
    <motion.aside
      initial={{ x: -250 }}
      animate={{ x: 0 }}
      className="w-64 bg-[#0e131d] border-r border-white/5 flex flex-col z-20 shrink-0"
    >
      {/* Logo */}
      <Link to="/" className="p-6 flex items-center gap-3 mb-4 group cursor-pointer">
        <div className="w-10 h-10 rounded-xl bg-[#00e5ff]/10 flex items-center justify-center border border-[#00e5ff]/20 shadow-[0_0_15px_rgba(0,229,255,0.1)] group-hover:bg-[#00e5ff]/20 transition-colors">
          <Hexagon className="text-[#00e5ff] w-6 h-6" />
        </div>
        <div>
          <h1 className="text-lg font-bold tracking-tight text-white leading-tight group-hover:text-[#00e5ff] transition-colors">
            HexMind
          </h1>
          <p className="text-[9px] font-serif italic text-white/50 tracking-widest uppercase">
            {t('sidebar.tagline')}
          </p>
        </div>
      </Link>

      {/* Navigation */}
      <nav className="flex-1 px-4 space-y-1">
        {navItems.map((item) => {
          const Icon = item.icon;
          const isActive =
            location.pathname === item.path ||
            (item.path !== '/' && location.pathname.startsWith(item.path));

          return (
            <Link
              key={item.nameKey}
              to={item.path}
              className={cn(
                'w-full flex items-center gap-4 px-4 py-3 rounded-xl transition-all duration-300 relative',
                isActive
                  ? item.highlight
                    ? 'bg-[#151a23] text-[#00e5ff] border border-white/5'
                    : 'bg-[#151a23] text-[#00e5ff] border border-transparent'
                  : 'text-white/50 hover:bg-white/[0.02] hover:text-white'
              )}
            >
              <Icon className="w-5 h-5" />
              <span className="font-medium text-sm">{t(item.nameKey)}</span>
              {isActive && !item.highlight && (
                <motion.div
                  layoutId="active-indicator"
                  className="absolute left-0 w-1 h-6 bg-[#00e5ff] rounded-r-full shadow-[0_0_10px_rgba(0,229,255,0.5)]"
                />
              )}
              {isActive && item.highlight && (
                <motion.div
                  layoutId="active-indicator"
                  className="absolute left-0 w-1 h-full bg-[#00e5ff] rounded-l-xl shadow-[0_0_10px_rgba(0,229,255,0.5)]"
                />
              )}
            </Link>
          );
        })}
      </nav>

      {/* Bottom Actions */}
      <div className="p-6 space-y-6">
        <Link
          to="/new"
          className="w-full flex items-center justify-center gap-2 py-3.5 rounded-xl bg-[#00e5ff] text-black font-bold text-sm hover:bg-[#00cce6] transition-colors shadow-[0_0_20px_rgba(0,229,255,0.2)]"
        >
          <Plus className="w-5 h-5" />
          {t('sidebar.newAnalysis')}
        </Link>

        {CLERK_ENABLED ? (
          <div className="flex items-center gap-3 px-1">
            <UserButton
              appearance={{
                elements: {
                  avatarBox: 'w-9 h-9',
                  userButtonPopoverCard: 'bg-[#0e131d] border border-white/10',
                  userButtonPopoverActionButton: 'text-white hover:bg-white/5',
                  userButtonPopoverActionButtonText: 'text-white',
                },
              }}
            />
            <span className="text-sm text-white/50 font-medium">Account</span>
          </div>
        ) : LOCAL_ONLY_MODE ? (
          <div className="rounded-2xl border border-white/5 bg-[#151a23] p-4">
            <p className="text-[10px] font-bold uppercase tracking-[0.15em] text-[#00e5ff]">
              {locale === 'en' ? 'Local Mode' : 'Local Mode'}
            </p>
            <p className="mt-2 text-sm text-white/60">
              {locale === 'en'
                ? 'Authentication is hidden. Preferences and drafts stay on this device.'
                : 'Authentication is hidden. Preferences and drafts stay on this device.'}
            </p>
          </div>
        ) : null}
      </div>
    </motion.aside>
  );
}
