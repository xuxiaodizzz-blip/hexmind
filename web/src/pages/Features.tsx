import { motion } from 'motion/react';
import { Link } from 'react-router-dom';
import {
  Hexagon,
  BrainCircuit,
  Network,
  ShieldAlert,
  BarChart3,
  Users,
  Zap,
  GitBranch,
  Globe,
  Lock,
  ArrowRight,
  Check,
} from 'lucide-react';

const features = [
  {
    icon: BrainCircuit,
    title: 'AI Persona Synthesis',
    description:
      'Create highly specialized AI agents with distinct domains, biases, and analytical frameworks. Each persona carries a custom system prompt that defines their expertise, communication style, and decision-making approach.',
    capabilities: [
      'Custom system prompts per persona',
      'Domain specialization (Tech, Business, Medical, Creative)',
      'Personal persona library with local + cloud sync',
      'Community sharing — make your personas public',
    ],
  },
  {
    icon: Network,
    title: 'Six Thinking Hats Protocol',
    description:
      'Force models through structured adversarial debate using the proven Six Thinking Hats framework. Blue Hat orchestrates, White Hat analyzes facts, Black Hat challenges, Yellow Hat explores benefits, Green Hat generates ideas, Red Hat gauges sentiment.',
    capabilities: [
      'Structured multi-round debate',
      'Multi-perspective adversarial analysis',
      'Automatic convergence detection',
      'Real-time decision tree mapping',
    ],
  },
  {
    icon: GitBranch,
    title: 'Decision Tree Visualization',
    description:
      'Watch your decision unfold in real-time as a visual node graph. Fork branches when experts disagree, merge when consensus emerges, and replay the entire reasoning chain anytime.',
    capabilities: [
      'Real-time node graph rendering',
      'Branch forking on disagreement',
      'Convergence visualization',
      'Full replay & export',
    ],
  },
  {
    icon: Zap,
    title: 'Token Budget Management',
    description:
      'Control costs with precise token budgets. Set limits per discussion, per round, and per persona. Monitor consumption in real-time with the token accountant.',
    capabilities: [
      'Per-discussion budget caps (128K–512K)',
      'Real-time token consumption tracking',
      'Cost estimation before launch',
      'Automatic early-stopping on budget exhaustion',
    ],
  },
  {
    icon: Users,
    title: 'Team Collaboration',
    description:
      'Invite team members with role-based access control. Share discussions, personas, and analytics across your organization.',
    capabilities: [
      'Role-based access (Owner, Admin, Member, Viewer)',
      'Team persona libraries',
      'Shared discussion history',
      'Audit trail for compliance',
    ],
  },
  {
    icon: BarChart3,
    title: 'Analytics & Insights',
    description:
      'Track your decision-making patterns over time. Understand which personas contribute most, which hat types dominate, and how confidence scores evolve.',
    capabilities: [
      'Hat usage distribution charts',
      'Confidence trend analysis',
      'Persona contribution metrics',
      'Weekly activity reports',
    ],
  },
  {
    icon: Globe,
    title: 'SSE Real-time Streaming',
    description:
      'Watch the discussion unfold live via Server-Sent Events. Each persona message, synthesis update, and convergence signal streams to you in real-time.',
    capabilities: [
      'Server-Sent Events (SSE) protocol',
      'Live persona message streaming',
      'Human intervention during discussion',
      'Graceful cancellation support',
    ],
  },
  {
    icon: Lock,
    title: 'Secure & Private',
    description:
      'Your decisions stay yours. JWT-based authentication, team-level isolation, and optional local-only mode with Ollama support.',
    capabilities: [
      'JWT token authentication',
      'Team-level data isolation',
      'Ollama local model support',
      'No data leaves your infrastructure',
    ],
  },
  {
    icon: ShieldAlert,
    title: 'Archive & Export',
    description:
      'Every discussion is archived with full metadata — rounds, personas, token usage, convergence scores. Export as Markdown or JSON for downstream processing.',
    capabilities: [
      'Automatic discussion archiving',
      'Full-text search across history',
      'Markdown & JSON export',
      'Metadata filtering & tagging',
    ],
  },
];

export default function Features() {
  return (
    <div className="min-h-screen bg-[#0b0f17] text-white">
      {/* Navbar */}
      <nav className="fixed top-0 w-full border-b border-white/5 bg-[#0b0f17]/80 backdrop-blur-md z-50">
        <div className="max-w-7xl mx-auto px-6 h-20 flex items-center justify-between">
          <Link to="/" className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-[#00e5ff]/10 flex items-center justify-center border border-[#00e5ff]/20">
              <Hexagon className="text-[#00e5ff] w-6 h-6" />
            </div>
            <div>
              <h1 className="text-xl font-bold tracking-tight text-white leading-tight">
                HexMind
              </h1>
              <p className="text-[10px] font-serif italic text-white/50 tracking-widest uppercase">
                The Ethereal Archive
              </p>
            </div>
          </Link>
          <div className="hidden md:flex items-center gap-8">
            <Link
              to="/"
              className="text-sm font-bold tracking-widest uppercase text-white/50 hover:text-white transition-colors"
            >
              Home
            </Link>
            <Link
              to="/app"
              className="px-6 py-2.5 rounded-xl bg-[#00e5ff] text-black font-bold text-sm hover:bg-[#00cce6] transition-colors shadow-[0_0_20px_rgba(0,229,255,0.2)]"
            >
              Launch App
            </Link>
          </div>
        </div>
      </nav>

      {/* Hero */}
      <div className="pt-40 pb-16 px-6 text-center relative">
        <div className="absolute top-0 left-0 w-full h-full overflow-hidden pointer-events-none">
          <div className="absolute top-[-10%] left-[-10%] w-[40%] h-[40%] bg-[#00e5ff]/10 rounded-full blur-[120px]" />
          <div className="absolute bottom-[-10%] right-[-10%] w-[40%] h-[40%] bg-[#b499ff]/10 rounded-full blur-[120px]" />
        </div>
        <div className="relative z-10 max-w-3xl mx-auto">
          <motion.h1
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            className="text-5xl lg:text-6xl font-bold font-sans tracking-tight mb-6"
          >
            Everything You Need for{' '}
            <span className="text-transparent bg-clip-text bg-gradient-to-r from-[#00e5ff] to-[#b499ff]">
              Better Decisions
            </span>
          </motion.h1>
          <motion.p
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.1 }}
            className="text-xl text-white/50 font-serif italic max-w-2xl mx-auto leading-relaxed"
          >
            AI-powered adversarial analysis with multi-persona debate, real-time
            streaming, and comprehensive analytics.
          </motion.p>
        </div>
      </div>

      {/* Feature Cards */}
      <div className="max-w-5xl mx-auto px-6 pb-24 space-y-6">
        {features.map((f, i) => (
          <motion.div
            key={i}
            initial={{ opacity: 0, y: 20 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            transition={{ delay: i * 0.05 }}
            className="bg-[#151a23] border border-white/5 rounded-2xl p-8 hover:border-white/10 transition-colors"
          >
            <div className="flex flex-col lg:flex-row gap-8">
              <div className="flex-1">
                <div className="flex items-center gap-4 mb-4">
                  <div className="w-12 h-12 rounded-xl bg-[#00e5ff]/10 flex items-center justify-center border border-[#00e5ff]/20">
                    <f.icon className="w-6 h-6 text-[#00e5ff]" />
                  </div>
                  <h2 className="text-2xl font-bold font-sans">{f.title}</h2>
                </div>
                <p className="text-white/50 font-serif italic leading-relaxed">
                  {f.description}
                </p>
              </div>
              <div className="lg:w-72 shrink-0">
                <ul className="space-y-2">
                  {f.capabilities.map((cap) => (
                    <li key={cap} className="flex items-start gap-2 text-sm text-white/70">
                      <Check className="w-4 h-4 text-[#00e5ff] mt-0.5 shrink-0" />
                      {cap}
                    </li>
                  ))}
                </ul>
              </div>
            </div>
          </motion.div>
        ))}
      </div>

      {/* CTA */}
      <div className="border-t border-white/5 bg-[#0e131d] py-24">
        <div className="max-w-3xl mx-auto text-center px-6">
          <motion.h2
            initial={{ opacity: 0, y: 20 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            className="text-3xl lg:text-4xl font-bold font-sans mb-6"
          >
            Ready to make better decisions?
          </motion.h2>
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            transition={{ delay: 0.1 }}
            className="flex flex-col sm:flex-row gap-4 justify-center"
          >
            <Link
              to="/register"
              className="px-8 py-4 rounded-xl bg-[#00e5ff] text-black font-bold text-lg hover:bg-[#00cce6] transition-colors shadow-[0_0_30px_rgba(0,229,255,0.3)] flex items-center justify-center gap-2"
            >
              Get Started Free <ArrowRight className="w-5 h-5" />
            </Link>
            <Link
              to="/app"
              className="px-8 py-4 rounded-xl bg-[#151a23] text-white font-bold text-lg border border-white/10 hover:bg-white/5 transition-colors text-center"
            >
              Try the Demo
            </Link>
          </motion.div>
        </div>
      </div>

      {/* Footer */}
      <footer className="border-t border-white/5 bg-[#0b0f17] py-12">
        <div className="max-w-7xl mx-auto px-6 flex flex-col md:flex-row items-center justify-between gap-6">
          <div className="flex items-center gap-3">
            <Hexagon className="text-white/30 w-5 h-5" />
            <span className="text-white/30 font-bold tracking-widest uppercase text-xs">
              HexMind © 2026
            </span>
          </div>
          <div className="flex gap-6 text-xs font-bold tracking-widest uppercase text-white/30">
            <Link to="/" className="hover:text-[#00e5ff] transition-colors">
              Home
            </Link>
            <Link to="/features" className="hover:text-[#00e5ff] transition-colors">
              Features
            </Link>
            <a href="#" className="hover:text-[#00e5ff] transition-colors">
              Privacy
            </a>
            <a href="#" className="hover:text-[#00e5ff] transition-colors">
              Terms
            </a>
          </div>
        </div>
      </footer>
    </div>
  );
}
