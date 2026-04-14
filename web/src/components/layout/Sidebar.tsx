import { Link, useLocation } from 'react-router-dom';
import { motion } from 'motion/react';
import {
  LayoutDashboard,
  MessageSquare,
  History,
  Users,
  FolderOpen,
  UsersRound,
  Settings as SettingsIcon,
  Plus,
  ArrowLeftRight,
  LogOut,
  Hexagon,
} from 'lucide-react';
import { cn } from '../../lib/utils';

const navItems = [
  { name: 'Dashboard', path: '/app', icon: LayoutDashboard },
  { name: 'New Discussion', path: '/app/new', icon: MessageSquare, highlight: true },
  { name: 'History', path: '/app/history', icon: History },
  { name: 'Personas', path: '/app/personas', icon: Users },
  { name: 'Assets', path: '/app/assets', icon: FolderOpen },
  { name: 'Teams', path: '/app/teams', icon: UsersRound },
  { name: 'Settings', path: '/app/settings', icon: SettingsIcon },
];

export default function Sidebar() {
  const location = useLocation();

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
            The Ethereal Archive
          </p>
        </div>
      </Link>

      {/* Navigation */}
      <nav className="flex-1 px-4 space-y-1">
        {navItems.map((item) => {
          const Icon = item.icon;
          const isActive =
            location.pathname === item.path ||
            (item.path !== '/app' && location.pathname.startsWith(item.path));

          return (
            <Link
              key={item.name}
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
              <span className="font-medium text-sm">{item.name}</span>
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
          to="/app/new"
          className="w-full flex items-center justify-center gap-2 py-3.5 rounded-xl bg-[#00e5ff] text-black font-bold text-sm hover:bg-[#00cce6] transition-colors shadow-[0_0_20px_rgba(0,229,255,0.2)]"
        >
          <Plus className="w-5 h-5" />
          New Analysis
        </Link>

        <div className="space-y-1 pt-4 border-t border-white/5">
          <button className="w-full flex items-center gap-4 px-4 py-2 text-white/50 hover:text-white transition-colors">
            <ArrowLeftRight className="w-4 h-4" />
            <span className="font-medium text-sm">Switch Team</span>
          </button>
          <Link
            to="/login"
            className="w-full flex items-center gap-4 px-4 py-2 text-white/50 hover:text-white transition-colors"
          >
            <LogOut className="w-4 h-4" />
            <span className="font-medium text-sm">Logout</span>
          </Link>
        </div>
      </div>
    </motion.aside>
  );
}
