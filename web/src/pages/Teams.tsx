import { motion } from 'motion/react';
import { Plus, UserPlus, Shield, Eye, Crown } from 'lucide-react';
import { cn } from '../lib/utils';

const teams = [
  {
    id: 'product-team',
    name: 'Product Decision Group',
    members: [
      { name: 'Zhang San', email: 'zhang@hexmind.ai', role: 'owner', avatar: 'https://picsum.photos/seed/zhang/40/40' },
      { name: 'Li Si', email: 'li@hexmind.ai', role: 'admin', avatar: 'https://picsum.photos/seed/lisi/40/40' },
      { name: 'Wang Wu', email: 'wang@hexmind.ai', role: 'member', avatar: 'https://picsum.photos/seed/wang/40/40' },
      { name: 'Zhao Liu', email: 'zhao@hexmind.ai', role: 'viewer', avatar: 'https://picsum.photos/seed/zhao/40/40' },
    ],
    current: true,
  },
  {
    id: 'tech-team',
    name: 'Tech Architecture Group',
    members: [
      { name: 'Zhang San', email: 'zhang@hexmind.ai', role: 'owner', avatar: 'https://picsum.photos/seed/zhang/40/40' },
      { name: 'Chen Qi', email: 'chen@hexmind.ai', role: 'member', avatar: 'https://picsum.photos/seed/chen/40/40' },
      { name: 'Liu Ba', email: 'liu@hexmind.ai', role: 'member', avatar: 'https://picsum.photos/seed/liuba/40/40' },
    ],
    current: false,
  },
];

const roleConfig: Record<string, { icon: typeof Crown; label: string; color: string }> = {
  owner: { icon: Crown, label: 'Owner', color: 'text-[#00e5ff]' },
  admin: { icon: Shield, label: 'Admin', color: 'text-[#b499ff]' },
  member: { icon: UserPlus, label: 'Member', color: 'text-white/70' },
  viewer: { icon: Eye, label: 'Viewer', color: 'text-white/40' },
};

export default function Teams() {
  return (
    <div className="flex-1 overflow-y-auto no-scrollbar p-8 lg:p-12 z-10 w-full bg-[#0b0f17] text-white">
      <div className="max-w-4xl mx-auto">
        {/* Header */}
        <div className="flex items-end justify-between mb-10 gap-6">
          <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }}>
            <h1 className="text-4xl font-bold font-sans mb-2 tracking-tight">Teams</h1>
            <p className="text-white/50 font-serif italic text-lg">Manage your teams and collaboration access.</p>
          </motion.div>
          <motion.button
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.1 }}
            className="flex items-center gap-2 bg-[#00e5ff] text-black px-5 py-2.5 rounded-xl font-bold text-sm hover:bg-[#00cce6] transition-colors shadow-[0_0_20px_rgba(0,229,255,0.2)]"
          >
            <Plus className="w-5 h-5" />
            Create Team
          </motion.button>
        </div>

        {/* Team Cards */}
        <div className="space-y-8">
          {teams.map((team, ti) => (
            <motion.div
              key={team.id}
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.15 + ti * 0.1 }}
              className={cn(
                'bg-[#151a23] border rounded-2xl p-8',
                team.current ? 'border-[#00e5ff]/30' : 'border-white/5'
              )}
            >
              <div className="flex items-center justify-between mb-6">
                <div className="flex items-center gap-3">
                  <h2 className="text-2xl font-bold font-sans">{team.name}</h2>
                  {team.current && (
                    <span className="text-[9px] font-bold tracking-[0.2em] text-[#00e5ff] uppercase bg-[#00e5ff]/10 px-2 py-0.5 rounded">
                      Current
                    </span>
                  )}
                </div>
                {!team.current && (
                  <button className="text-sm font-bold text-white/50 hover:text-white transition-colors">Switch →</button>
                )}
              </div>

              {/* Members */}
              <div className="space-y-3 mb-6">
                {team.members.map((m) => {
                  const rc = roleConfig[m.role];
                  const Icon = rc.icon;
                  return (
                    <div key={m.email} className="flex items-center justify-between p-3 bg-[#1e2430] rounded-xl border border-white/5">
                      <div className="flex items-center gap-3">
                        <img src={m.avatar} className="w-10 h-10 rounded-full border border-white/10" alt={m.name} referrerPolicy="no-referrer" />
                        <div>
                          <p className="font-sans font-medium text-sm">{m.name}</p>
                          <p className="text-xs text-white/40">{m.email}</p>
                        </div>
                      </div>
                      <div className={cn('flex items-center gap-2', rc.color)}>
                        <Icon className="w-4 h-4" />
                        <span className="text-xs font-bold tracking-widest uppercase">{rc.label}</span>
                      </div>
                    </div>
                  );
                })}
              </div>

              {/* Add Member */}
              {team.current && (
                <div className="flex gap-3">
                  <input
                    type="email"
                    placeholder="Enter email to invite..."
                    className="flex-1 bg-[#1e2430] border border-white/10 rounded-xl px-4 py-3 text-sm text-white placeholder:text-white/30 focus:outline-none focus:border-[#00e5ff]/50 transition-colors"
                  />
                  <select className="bg-[#1e2430] border border-white/10 rounded-xl px-4 py-3 text-sm text-white/80 focus:outline-none">
                    <option value="member">Member</option>
                    <option value="admin">Admin</option>
                    <option value="viewer">Viewer</option>
                  </select>
                  <button className="px-6 py-3 bg-[#00e5ff] text-black font-bold text-sm rounded-xl hover:bg-[#00cce6] transition-colors">
                    Invite
                  </button>
                </div>
              )}
            </motion.div>
          ))}
        </div>
      </div>
    </div>
  );
}
