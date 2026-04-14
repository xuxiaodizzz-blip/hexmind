import { motion } from 'motion/react';
import { Link } from 'react-router-dom';
import { Hexagon, ArrowRight, BrainCircuit, Network, ShieldAlert } from 'lucide-react';

export default function LandingPage() {
  return (
    <div className="h-full overflow-y-auto no-scrollbar bg-[#0b0f17] text-white selection:bg-[#00e5ff]/30 relative">
      {/* Background Effects */}
      <div className="absolute top-0 left-0 w-full h-full overflow-hidden pointer-events-none">
        <div className="absolute top-[-10%] left-[-10%] w-[40%] h-[40%] bg-[#00e5ff]/10 rounded-full blur-[120px]" />
        <div className="absolute bottom-[-10%] right-[-10%] w-[40%] h-[40%] bg-[#b499ff]/10 rounded-full blur-[120px]" />
        <div className="absolute inset-0 bg-[url('https://grainy-gradients.vercel.app/noise.svg')] opacity-20 mix-blend-overlay"></div>
      </div>

      {/* Navbar */}
      <nav className="fixed top-0 w-full border-b border-white/5 bg-[#0b0f17]/80 backdrop-blur-md z-50">
        <div className="max-w-7xl mx-auto px-6 h-20 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-[#00e5ff]/10 flex items-center justify-center border border-[#00e5ff]/20 shadow-[0_0_15px_rgba(0,229,255,0.1)]">
              <Hexagon className="text-[#00e5ff] w-6 h-6" />
            </div>
            <div>
              <h1 className="text-xl font-bold tracking-tight text-white leading-tight">HexMind</h1>
              <p className="text-[10px] font-serif italic text-white/50 tracking-widest uppercase">The Ethereal Archive</p>
            </div>
          </div>
          <div className="hidden md:flex items-center gap-8">
            <a href="#features" className="text-sm font-bold tracking-widest uppercase text-white/50 hover:text-white transition-colors">Features</a>
            <a href="#technology" className="text-sm font-bold tracking-widest uppercase text-white/50 hover:text-white transition-colors">Technology</a>
            <Link to="/features" className="text-sm font-bold tracking-widest uppercase text-white/50 hover:text-white transition-colors">All Features</Link>
            <Link to="/login" className="text-sm font-bold tracking-widest uppercase text-white/50 hover:text-white transition-colors">Login</Link>
            <Link to="/app" className="px-6 py-2.5 rounded-xl bg-[#00e5ff] text-black font-bold text-sm hover:bg-[#00cce6] transition-colors shadow-[0_0_20px_rgba(0,229,255,0.2)]">
              Launch App
            </Link>
          </div>
        </div>
      </nav>

      {/* Hero Section */}
      <div className="relative pt-40 pb-24 lg:pt-56 lg:pb-40 px-6 z-10">
        <div className="max-w-5xl mx-auto text-center">
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            className="inline-flex items-center gap-2 px-4 py-2 rounded-full bg-white/5 border border-white/10 mb-8"
          >
            <span className="w-2 h-2 rounded-full bg-[#00e5ff] animate-pulse shadow-[0_0_8px_rgba(0,229,255,0.8)]" />
            <span className="text-[10px] font-bold tracking-[0.2em] text-white/70 uppercase">HexMind Protocol v2.0 Live</span>
          </motion.div>

          <motion.h1
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.1 }}
            className="text-5xl lg:text-7xl font-bold font-sans tracking-tight mb-8 leading-[1.1]"
          >
            Orchestrate Your Fleet of <br />
            <span className="text-transparent bg-clip-text bg-gradient-to-r from-[#00e5ff] via-[#b499ff] to-[#00e5ff] bg-300% animate-gradient">
              Digital Specialists
            </span>
          </motion.h1>

          <motion.p
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.2 }}
            className="text-xl text-white/50 font-serif italic max-w-2xl mx-auto mb-12 leading-relaxed"
          >
            "A multiplicity of perspectives is the only shield against the singularity of error." Assemble, configure, and deploy AI personas for complex adversarial debates.
          </motion.p>

          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.3 }}
            className="flex flex-col sm:flex-row items-center justify-center gap-4"
          >
            <Link
              to="/app"
              className="w-full sm:w-auto px-8 py-4 rounded-xl bg-[#00e5ff] text-black font-bold text-lg hover:bg-[#00cce6] transition-all hover:scale-105 shadow-[0_0_30px_rgba(0,229,255,0.3)] flex items-center justify-center gap-2"
            >
              Enter the Archive <ArrowRight className="w-5 h-5" />
            </Link>
            <Link
              to="/register"
              className="w-full sm:w-auto px-8 py-4 rounded-xl bg-[#151a23] text-white font-bold text-lg border border-white/10 hover:bg-white/5 transition-colors text-center"
            >
              Create Account
            </Link>
          </motion.div>
        </div>
      </div>

      {/* Features Grid */}
      <div id="features" className="py-24 bg-[#0e131d] border-y border-white/5 relative z-10">
        <div className="max-w-7xl mx-auto px-6">
          <div className="text-center mb-20">
            <h2 className="text-3xl lg:text-4xl font-bold font-sans mb-4">Architected for Complexity</h2>
            <p className="text-white/50 font-serif italic text-lg">Beyond simple prompts. True cognitive synthesis.</p>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
            {[
              {
                icon: BrainCircuit,
                title: 'Persona Synthesis',
                desc: 'Create highly specialized AI agents with distinct domains, biases, and analytical frameworks. From Quantum Architects to Legal Antagonists.',
              },
              {
                icon: Network,
                title: 'Adversarial Debate',
                desc: 'Force models to argue, find edge cases, and reach consensus through structured multi-agent protocols and decision mapping.',
              },
              {
                icon: ShieldAlert,
                title: 'Algorithmic Patrimony',
                desc: 'Secure your intellectual property with enterprise-grade containment, verifiable decision mapping, and strict token budgets.',
              },
            ].map((f, i) => (
              <motion.div
                key={i}
                initial={{ opacity: 0, y: 20 }}
                whileInView={{ opacity: 1, y: 0 }}
                viewport={{ once: true }}
                transition={{ delay: i * 0.1 }}
                className="bg-[#151a23] border border-white/5 rounded-3xl p-8 hover:border-[#00e5ff]/30 transition-colors group relative overflow-hidden"
              >
                <div className="absolute top-0 right-0 w-32 h-32 bg-[#00e5ff]/5 rounded-bl-full -mr-16 -mt-16 transition-transform group-hover:scale-150" />
                <div className="w-14 h-14 rounded-2xl bg-[#00e5ff]/10 flex items-center justify-center mb-8 group-hover:scale-110 transition-transform border border-[#00e5ff]/20">
                  <f.icon className="w-7 h-7 text-[#00e5ff]" />
                </div>
                <h3 className="text-xl font-bold font-sans mb-4 text-white/90">{f.title}</h3>
                <p className="text-white/50 leading-relaxed font-serif italic">{f.desc}</p>
              </motion.div>
            ))}
          </div>
        </div>
      </div>

      {/* Stats */}
      <div id="technology" className="py-24 relative z-10">
        <div className="max-w-7xl mx-auto px-6">
          <div className="grid grid-cols-2 md:grid-cols-4 gap-8 border border-white/5 rounded-3xl bg-[#151a23]/50 p-12 backdrop-blur-sm">
            {[
              { label: 'Active Personas', value: '10,000+' },
              { label: 'Decisions Mapped', value: '2.4M' },
              { label: 'Avg. Consensus Time', value: '12s' },
              { label: 'System Uptime', value: '99.99%' },
            ].map((stat, i) => (
              <div key={i} className="text-center">
                <p className="text-4xl font-bold font-sans text-white mb-2">{stat.value}</p>
                <p className="text-[10px] font-bold tracking-[0.2em] text-[#00e5ff] uppercase">{stat.label}</p>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Footer */}
      <footer className="border-t border-white/5 bg-[#0e131d] py-12 relative z-10">
        <div className="max-w-7xl mx-auto px-6 flex flex-col md:flex-row items-center justify-between gap-6">
          <div className="flex items-center gap-3">
            <Hexagon className="text-white/30 w-5 h-5" />
            <span className="text-white/30 font-bold tracking-widest uppercase text-xs">HexMind © 2026</span>
          </div>
          <div className="flex gap-6 text-xs font-bold tracking-widest uppercase text-white/30">
            <a href="#" className="hover:text-[#00e5ff] transition-colors">Privacy</a>
            <a href="#" className="hover:text-[#00e5ff] transition-colors">Terms</a>
            <a href="#" className="hover:text-[#00e5ff] transition-colors">Protocol</a>
          </div>
        </div>
      </footer>
    </div>
  );
}
