import { motion } from 'motion/react';
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Legend, PieChart, Pie, Cell } from 'recharts';

const hatData = [
  { name: 'White', value: 28, color: '#E5E7EB' },
  { name: 'Red', value: 12, color: '#EF4444' },
  { name: 'Black', value: 22, color: '#374151' },
  { name: 'Yellow', value: 18, color: '#F59E0B' },
  { name: 'Green', value: 15, color: '#10B981' },
  { name: 'Blue', value: 5, color: '#3B82F6' },
];

const weeklyData = [
  { name: 'Mon', discussions: 4, tokens: 24000 },
  { name: 'Tue', discussions: 3, tokens: 18000 },
  { name: 'Wed', discussions: 6, tokens: 52000 },
  { name: 'Thu', discussions: 5, tokens: 39000 },
  { name: 'Fri', discussions: 2, tokens: 14000 },
  { name: 'Sat', discussions: 1, tokens: 8000 },
  { name: 'Sun', discussions: 3, tokens: 21000 },
];

const confidenceData = [
  { range: '<50%', count: 3 },
  { range: '50-70%', count: 12 },
  { range: '70-90%', count: 25 },
  { range: '>90%', count: 7 },
];

export default function Analytics() {
  return (
    <div className="flex-1 overflow-y-auto no-scrollbar p-8 lg:p-12 z-10 w-full bg-[#0b0f17] text-white">
      <div className="max-w-6xl mx-auto">
        <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} className="mb-10">
          <h1 className="text-4xl font-bold font-sans mb-2 tracking-tight">Analytics</h1>
          <p className="text-white/50 font-serif italic text-lg">Deep dive into your decision patterns and usage metrics.</p>
        </motion.div>

        {/* Summary Cards */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-10">
          {[
            { label: 'Total Discussions', value: '47' },
            { label: 'Total Tokens', value: '2.3M' },
            { label: 'Total Cost', value: '$12.50' },
            { label: 'Avg Confidence', value: '76%' },
          ].map((stat, i) => (
            <motion.div
              key={stat.label}
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.1 + i * 0.05 }}
              className="bg-[#151a23] border border-white/5 rounded-2xl p-6 text-center"
            >
              <p className="text-3xl font-bold font-sans text-white mb-1">{stat.value}</p>
              <p className="text-[10px] font-bold tracking-[0.2em] text-[#00e5ff] uppercase">{stat.label}</p>
            </motion.div>
          ))}
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-10">
          {/* Hat Distribution Pie Chart */}
          <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.3 }} className="bg-[#151a23] border border-white/5 rounded-2xl p-6">
            <h3 className="font-sans font-bold text-lg mb-6">Hat Usage Distribution</h3>
            <div className="h-64 w-full">
              <ResponsiveContainer width="100%" height="100%">
                <PieChart>
                  <Pie data={hatData} cx="50%" cy="50%" innerRadius={60} outerRadius={100} paddingAngle={2} dataKey="value">
                    {hatData.map((entry, index) => (
                      <Cell key={`cell-${index}`} fill={entry.color} />
                    ))}
                  </Pie>
                  <Tooltip
                    contentStyle={{
                      backgroundColor: '#252a35',
                      borderColor: '#3b494c',
                      borderRadius: '8px',
                      color: '#dee2f1',
                    }}
                  />
                  <Legend
                    formatter={(value) => <span style={{ color: '#bac9cc', fontSize: '12px' }}>{value}</span>}
                  />
                </PieChart>
              </ResponsiveContainer>
            </div>
          </motion.div>

          {/* Confidence Distribution */}
          <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.4 }} className="bg-[#151a23] border border-white/5 rounded-2xl p-6">
            <h3 className="font-sans font-bold text-lg mb-6">Confidence Distribution</h3>
            <div className="h-64 w-full">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={confidenceData} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#3b494c" vertical={false} />
                  <XAxis dataKey="range" stroke="#bac9cc" fontSize={12} tickLine={false} axisLine={false} />
                  <YAxis stroke="#bac9cc" fontSize={12} tickLine={false} axisLine={false} />
                  <Tooltip
                    contentStyle={{
                      backgroundColor: '#252a35',
                      borderColor: '#3b494c',
                      borderRadius: '8px',
                      color: '#dee2f1',
                    }}
                  />
                  <Bar dataKey="count" fill="#00e5ff" radius={[4, 4, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
            </div>
          </motion.div>
        </div>

        {/* Weekly Activity */}
        <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.5 }} className="bg-[#151a23] border border-white/5 rounded-2xl p-6 mb-10">
          <h3 className="font-sans font-bold text-lg mb-6">Weekly Activity</h3>
          <div className="h-72 w-full">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={weeklyData} margin={{ top: 20, right: 30, left: 20, bottom: 5 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#3b494c" vertical={false} />
                <XAxis dataKey="name" stroke="#bac9cc" tickLine={false} axisLine={false} />
                <YAxis yAxisId="left" stroke="#bac9cc" tickLine={false} axisLine={false} />
                <YAxis yAxisId="right" orientation="right" stroke="#bac9cc" tickLine={false} axisLine={false} />
                <Tooltip
                  contentStyle={{
                    backgroundColor: '#252a35',
                    borderColor: '#3b494c',
                    borderRadius: '8px',
                    color: '#dee2f1',
                  }}
                />
                <Legend formatter={(value) => <span style={{ color: '#bac9cc', fontSize: '12px' }}>{value}</span>} />
                <Bar yAxisId="left" dataKey="discussions" name="Discussions" fill="#00e5ff" radius={[4, 4, 0, 0]} />
                <Bar yAxisId="right" dataKey="tokens" name="Tokens" fill="#b499ff" radius={[4, 4, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </motion.div>

        {/* Persona Contribution */}
        <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.6 }} className="bg-[#151a23] border border-white/5 rounded-2xl p-6">
          <h3 className="font-sans font-bold text-lg mb-6">Persona Contributions</h3>
          <div className="space-y-4">
            {[
              { name: 'Backend Engineer', discussions: 23, hats: ['bg-white', 'bg-white', 'bg-gray-800', 'bg-gray-800', 'bg-green-500'] },
              { name: 'Product Manager', discussions: 18, hats: ['bg-yellow-400', 'bg-yellow-400', 'bg-red-500', 'bg-white'] },
              { name: 'CFO', discussions: 12, hats: ['bg-gray-800', 'bg-gray-800', 'bg-yellow-400'] },
              { name: 'Clinical Analyst', discussions: 8, hats: ['bg-white', 'bg-blue-500', 'bg-green-500'] },
            ].map((p) => (
              <div key={p.name} className="flex items-center gap-4 p-3 bg-[#1e2430] rounded-xl border border-white/5">
                <span className="font-sans font-medium text-sm w-40">{p.name}</span>
                <div className="flex-1 h-2 bg-[#0b0f17] rounded-full overflow-hidden">
                  <div className="h-full bg-[#00e5ff] rounded-full" style={{ width: `${(p.discussions / 23) * 100}%` }} />
                </div>
                <span className="text-sm font-bold w-8 text-right">{p.discussions}</span>
                <div className="flex gap-1 w-24 justify-end">
                  {p.hats.map((hat, hi) => (
                    <div key={hi} className={`w-2 h-2 rounded-full ${hat}`} />
                  ))}
                </div>
              </div>
            ))}
          </div>
        </motion.div>
      </div>
    </div>
  );
}
