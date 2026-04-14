import { motion } from 'motion/react';
import { Link } from 'react-router-dom';
import { Activity, Users, Cpu } from 'lucide-react';
import { AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts';
import { cn } from '../lib/utils';

const chartData = [
  { name: 'Week 1', discussions: 12 },
  { name: 'Week 2', discussions: 19 },
  { name: 'Week 3', discussions: 15 },
  { name: 'Week 4', discussions: 28 },
  { name: 'Week 5', discussions: 24 },
  { name: 'Week 6', discussions: 32 },
  { name: 'Week 7', discussions: 38 },
];

const recentDiscussions = [
  { id: '1', question: 'Should we migrate from MySQL to PostgreSQL?', status: 'completed', confidence: 78, personas: 3, rounds: 8, date: '2026-04-12' },
  { id: '2', question: 'Is launching a paid tier before Series A advisable?', status: 'running', confidence: 0, personas: 4, rounds: 3, date: '2026-04-13' },
  { id: '3', question: 'Should we adopt a microservices architecture?', status: 'completed', confidence: 85, personas: 3, rounds: 6, date: '2026-04-11' },
];

export default function Overview() {
  return (
    <div className="flex-1 overflow-y-auto no-scrollbar p-8 z-10">
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.1 }}
        className="mb-8"
      >
        <h2 className="text-3xl font-bold font-sans mb-2">Welcome back, Commander</h2>
        <p className="text-on-surface-variant">Here is what's happening with your decisions today.</p>
      </motion.div>

      {/* Stats Grid */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-8">
        {[
          { title: 'Total Discussions', value: '47', change: '+14.5%', icon: Activity, color: 'text-primary' },
          { title: 'Active Personas', value: '24', change: '+3', icon: Users, color: 'text-secondary' },
          { title: 'Token Budget Used', value: '2.3M', change: '$12.50', icon: Cpu, color: 'text-tertiary' },
        ].map((stat, i) => {
          const Icon = stat.icon;
          return (
            <motion.div
              key={stat.title}
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.2 + i * 0.1 }}
              className="glass-panel ghost-border rounded-2xl p-6 relative overflow-hidden group"
            >
              <div className="absolute -right-6 -top-6 w-24 h-24 bg-surface-container-high rounded-full opacity-50 group-hover:scale-150 transition-transform duration-700 ease-out" />
              <div className="relative z-10 flex justify-between items-start mb-4">
                <div>
                  <p className="text-on-surface-variant font-sans text-sm font-medium mb-1">{stat.title}</p>
                  <h3 className="text-3xl font-bold font-sans">{stat.value}</h3>
                </div>
                <div className={cn('w-12 h-12 rounded-xl bg-surface-container flex items-center justify-center ghost-border', stat.color)}>
                  <Icon className="w-6 h-6" />
                </div>
              </div>
              <div className="relative z-10 flex items-center gap-2">
                <span className="text-primary text-sm font-medium font-sans bg-primary/10 px-2 py-0.5 rounded">
                  {stat.change}
                </span>
                <span className="text-on-surface-variant text-sm">vs last month</span>
              </div>
            </motion.div>
          );
        })}
      </div>

      {/* Charts & Recent */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Main Chart */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.5 }}
          className="lg:col-span-2 glass-panel ghost-border rounded-2xl p-6"
        >
          <div className="flex justify-between items-center mb-6">
            <h3 className="font-sans font-bold text-lg">Discussion Activity</h3>
            <select className="bg-surface-container-low border border-outline-variant/50 rounded-lg px-3 py-1.5 text-sm font-sans focus:outline-none">
              <option>Last 7 weeks</option>
              <option>Last 30 days</option>
              <option>This Year</option>
            </select>
          </div>
          <div className="h-72 w-full">
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart data={chartData} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
                <defs>
                  <linearGradient id="colorDiscussions" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="var(--color-primary)" stopOpacity={0.3} />
                    <stop offset="95%" stopColor="var(--color-primary)" stopOpacity={0} />
                  </linearGradient>
                </defs>
                <CartesianGrid strokeDasharray="3 3" stroke="var(--color-outline-variant)" vertical={false} />
                <XAxis dataKey="name" stroke="var(--color-on-surface-variant)" fontSize={12} tickLine={false} axisLine={false} />
                <YAxis stroke="var(--color-on-surface-variant)" fontSize={12} tickLine={false} axisLine={false} />
                <Tooltip
                  contentStyle={{
                    backgroundColor: 'var(--color-surface-container-high)',
                    borderColor: 'var(--color-outline-variant)',
                    borderRadius: '8px',
                    color: 'var(--color-on-surface)',
                  }}
                  itemStyle={{ color: 'var(--color-primary)' }}
                />
                <Area type="monotone" dataKey="discussions" stroke="var(--color-primary)" strokeWidth={3} fillOpacity={1} fill="url(#colorDiscussions)" />
              </AreaChart>
            </ResponsiveContainer>
          </div>
        </motion.div>

        {/* Recent Discussions */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.6 }}
          className="glass-panel ghost-border rounded-2xl p-6 flex flex-col"
        >
          <div className="flex justify-between items-center mb-6">
            <h3 className="font-sans font-bold text-lg">Recent Discussions</h3>
            <Link to="/app/history" className="text-primary hover:text-primary-fixed transition-colors text-sm font-medium">
              View all →
            </Link>
          </div>

          <div className="flex-1 space-y-4">
            {recentDiscussions.map((d) => (
              <Link
                key={d.id}
                to={`/app/discussion/${d.id}`}
                className="block p-3 rounded-lg bg-surface-container-low ghost-border hover:bg-surface-container transition-colors"
              >
                <p className="font-sans text-sm mb-2 line-clamp-2">{d.question}</p>
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <span
                      className={cn(
                        'w-2 h-2 rounded-full',
                        d.status === 'running' ? 'bg-primary animate-pulse neon-glow' : 'bg-green-500'
                      )}
                    />
                    <span className="text-[10px] font-bold tracking-widest text-on-surface-variant uppercase">
                      {d.status === 'running' ? 'Live' : `${d.confidence}%`}
                    </span>
                  </div>
                  <span className="font-mono text-xs text-on-surface-variant">{d.date}</span>
                </div>
              </Link>
            ))}
          </div>
        </motion.div>
      </div>
    </div>
  );
}
