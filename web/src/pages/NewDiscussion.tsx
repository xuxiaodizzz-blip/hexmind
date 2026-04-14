import { useState } from 'react';
import { motion } from 'motion/react';
import { useNavigate } from 'react-router-dom';
import { Settings2, ArrowLeft, ArrowRight } from 'lucide-react';
import { cn } from '../lib/utils';
import { Select, Slider } from '../components/ui';
import { SYSTEM_PERSONAS, LLM_MODELS, LIMITS } from '../data/personas';
import * as api from '../lib/api';

export default function NewDiscussion() {
  const navigate = useNavigate();
  const [step, setStep] = useState(1);
  const [question, setQuestion] = useState('');
  const [selected, setSelected] = useState<string[]>([]);
  const [model, setModel] = useState('gpt-4o');
  const [maxRounds, setMaxRounds] = useState(12);
  const [tokenBudget, setTokenBudget] = useState(LIMITS.TOKEN_BUDGET_DEFAULT);
  const [launching, setLaunching] = useState(false);
  const [error, setError] = useState('');

  const toggleExpert = (id: string) => {
    setSelected((prev) =>
      prev.includes(id)
        ? prev.filter((x) => x !== id)
        : prev.length < LIMITS.PERSONA_MAX
          ? [...prev, id]
          : prev,
    );
  };

  const handleStart = async () => {
    setError('');
    setLaunching(true);
    try {
      const res = await api.createDiscussion({
        question,
        persona_ids: selected,
        config: { model, token_budget: tokenBudget, locale: 'zh' },
      });
      navigate(`/app/discussion/${res.discussion_id}`);
    } catch (err) {
      setError(err instanceof api.ApiError ? err.message : '创建讨论失败');
    } finally {
      setLaunching(false);
    }
  };

  return (
    <div className="flex-1 overflow-y-auto no-scrollbar p-8 lg:p-12 z-10 w-full bg-[#0b0f17] text-white">
      <div className="max-w-6xl mx-auto">
        {/* Wizard Header */}
        <div className="mb-10">
          <div className="flex items-center gap-2 mb-6">
            <span className="text-[10px] font-bold tracking-[0.2em] text-white/50 uppercase">Wizard Mode</span>
            <div className="flex gap-1.5">
              {[1, 2, 3].map((s) => (
                <div
                  key={s}
                  className={cn('w-2 h-2 rounded-full', s <= step ? 'bg-white' : 'bg-white/20')}
                />
              ))}
            </div>
          </div>
          <motion.h1 initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} className="text-4xl font-bold font-sans mb-2 tracking-tight">
            {step === 1 && 'Define Your Question'}
            {step === 2 && 'Configure Discussion'}
            {step === 3 && 'Review & Launch'}
          </motion.h1>
          <motion.p initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.1 }} className="text-white/50 font-serif italic text-xl">
            {step === 1 && 'Step 1: What decision do you need to make?'}
            {step === 2 && 'Step 2: Assemble your digital think-tank.'}
            {step === 3 && 'Step 3: Confirm and start the analysis.'}
          </motion.p>
        </div>

        {/* Step 1: Question */}
        {step === 1 && (
          <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.2 }} className="max-w-3xl">
            <textarea
              value={question}
              onChange={(e) => setQuestion(e.target.value)}
              placeholder="e.g. How should we architect the decentralized liquidity protocol to ensure maximum security while maintaining sub-second latency?"
              className="w-full h-48 bg-[#151a23] border border-white/10 rounded-2xl p-6 text-lg text-white placeholder:text-white/30 focus:outline-none focus:border-[#00e5ff]/50 transition-colors resize-none font-serif italic"
            />
            <div className="mt-6">
              <p className="text-[10px] font-bold tracking-[0.15em] text-white/40 uppercase mb-3">Good question examples:</p>
              <div className="space-y-2">
                {[
                  'Should we launch a paid tier before Series A?',
                  'Is migrating from MySQL to PostgreSQL worth the effort?',
                  'Should we adopt a microservices architecture?',
                ].map((ex) => (
                  <button
                    key={ex}
                    onClick={() => setQuestion(ex)}
                    className="block text-left text-sm text-white/50 hover:text-white/80 transition-colors font-serif italic"
                  >
                    → "{ex}"
                  </button>
                ))}
              </div>
            </div>
            <div className="mt-10 flex justify-end">
              <button
                onClick={() => question && setStep(2)}
                disabled={!question}
                className="flex items-center gap-2 px-8 py-3 bg-[#00e5ff] text-black font-bold rounded-xl hover:bg-[#00cce6] transition-colors disabled:opacity-30 disabled:cursor-not-allowed"
              >
                Next <ArrowRight className="w-4 h-4" />
              </button>
            </div>
          </motion.div>
        )}

        {/* Step 2: Select Experts + Parameters */}
        {step === 2 && (
          <div className="flex flex-col lg:flex-row gap-8">
            <div className="flex-1 space-y-10">
              {/* Display query */}
              <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.2 }}>
                <h3 className="text-[10px] font-bold tracking-[0.2em] text-white/40 uppercase mb-4">Primary Inquiry</h3>
                <div className="bg-transparent border-l-2 border-[#00e5ff] pl-6 py-2">
                  <p className="font-serif italic text-2xl text-white/90 leading-relaxed">"{question}"</p>
                </div>
              </motion.div>

              {/* Select Experts */}
              <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.3 }}>
                <div className="flex items-end justify-between mb-6">
                  <div>
                    <h2 className="text-2xl font-bold font-sans mb-1">Select Experts</h2>
                    <div className="flex items-center gap-2 text-sm text-white/60">
                      <div className="w-3 h-3 rounded-sm bg-[#00e5ff]/20 flex items-center justify-center">
                        <div className="w-1 h-1 bg-[#00e5ff] rounded-full" />
                      </div>
                      Selected: {selected.length}/{LIMITS.PERSONA_MAX}
                    </div>
                  </div>
                </div>

                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  {SYSTEM_PERSONAS.map((expert) => {
                    const isSelected = selected.includes(expert.id);
                    return (
                      <div
                        key={expert.id}
                        onClick={() => toggleExpert(expert.id)}
                        className={cn(
                          'rounded-2xl p-5 cursor-pointer relative overflow-hidden transition-colors',
                          isSelected
                            ? 'bg-[#151a23] border border-[#00e5ff] shadow-[0_0_20px_rgba(0,229,255,0.1)]'
                            : 'bg-[#151a23] border border-white/5 hover:border-white/20'
                        )}
                      >
                        {isSelected && <div className="absolute inset-0 bg-[#00e5ff]/5" />}
                        <div className="relative z-10">
                          <div className="flex justify-between items-start mb-4">
                            <img
                              src={expert.avatar}
                              className={cn('w-12 h-12 rounded-xl object-cover border border-white/10', !isSelected && 'grayscale opacity-70')}
                              alt={expert.name}
                              referrerPolicy="no-referrer"
                            />
                            <span className="text-[10px] bg-white/5 text-white/50 px-2 py-0.5 rounded border border-white/5 capitalize">{expert.domain}</span>
                          </div>
                          <h3 className={cn('text-lg font-bold font-sans mb-0.5', isSelected ? 'text-white' : 'text-white/80')}>
                            {expert.name}
                          </h3>
                          <p className={cn('text-sm mb-4', isSelected ? 'text-white/50' : 'text-white/40')}>{expert.role}</p>
                          <div className="flex gap-2 flex-wrap">
                            {expert.tags.map((tag) => (
                              <span key={tag} className="text-[10px] bg-white/5 text-white/60 px-2 py-1 rounded border border-white/5">
                                {tag}
                              </span>
                            ))}
                          </div>
                        </div>
                      </div>
                    );
                  })}
                </div>
              </motion.div>

              <div className="flex gap-4">
                <button
                  onClick={() => setStep(1)}
                  className="flex items-center gap-2 px-6 py-3 bg-[#151a23] text-white/70 font-bold rounded-xl border border-white/10 hover:bg-white/5 transition-colors"
                >
                  <ArrowLeft className="w-4 h-4" /> Back
                </button>
                <button
                  onClick={() => selected.length >= LIMITS.PERSONA_MIN && setStep(3)}
                  disabled={selected.length < LIMITS.PERSONA_MIN}
                  className="flex items-center gap-2 px-8 py-3 bg-[#00e5ff] text-black font-bold rounded-xl hover:bg-[#00cce6] transition-colors disabled:opacity-30 disabled:cursor-not-allowed"
                >
                  Next <ArrowRight className="w-4 h-4" />
                </button>
              </div>
            </div>

            {/* Right Column - Parameters */}
            <motion.div initial={{ opacity: 0, x: 20 }} animate={{ opacity: 1, x: 0 }} transition={{ delay: 0.4 }} className="w-full lg:w-80 shrink-0">
              <div className="bg-[#151a23] border border-white/5 rounded-2xl p-6 sticky top-8">
                <div className="flex items-center gap-3 mb-8">
                  <Settings2 className="w-5 h-5 text-white/70" />
                  <h2 className="text-xl font-bold font-sans">Parameters</h2>
                </div>

                <div className="space-y-8 mb-10">
                  <div>
                    <label className="block text-[10px] font-bold tracking-[0.15em] text-white/50 uppercase mb-3">LLM Model</label>
                    <Select options={LLM_MODELS} value={model} onChange={setModel} />
                  </div>

                  <div>
                    <div className="flex justify-between items-center mb-3">
                      <label className="text-[10px] font-bold tracking-[0.15em] text-white/50 uppercase">Max Rounds</label>
                      <span className="font-bold text-sm">{String(maxRounds).padStart(2, '0')}</span>
                    </div>
                    <Slider value={maxRounds} min={2} max={24} step={1} onChange={setMaxRounds} minLabel="Concise" maxLabel="Exhaustive" />
                  </div>

                  <div>
                    <div className="flex justify-between items-center mb-3">
                      <label className="text-[10px] font-bold tracking-[0.15em] text-white/50 uppercase">Token Budget</label>
                      <span className="font-bold text-sm">{(tokenBudget / 1000).toFixed(0)}k</span>
                    </div>
                    <Slider value={tokenBudget} min={LIMITS.TOKEN_BUDGET_MIN} max={LIMITS.TOKEN_BUDGET_MAX} step={LIMITS.TOKEN_BUDGET_STEP} onChange={setTokenBudget} minLabel="Eco" maxLabel="Omniscient" />
                  </div>
                </div>

                <div className="space-y-3 mb-8 border-t border-white/10 pt-6">
                  <div className="flex justify-between items-center text-sm">
                    <span className="text-white/50 font-serif italic">Active Experts:</span>
                    <span className="font-bold">{String(selected.length).padStart(2, '0')}</span>
                  </div>
                  <div className="flex justify-between items-center text-sm">
                    <span className="text-white/50 font-serif italic">Protocol:</span>
                    <span className="font-bold text-white/90">Six Thinking Hats</span>
                  </div>
                </div>
              </div>
            </motion.div>
          </div>
        )}

        {/* Step 3: Review & Launch */}
        {step === 3 && (
          <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.2 }} className="max-w-2xl">
            <div className="bg-[#151a23] border border-white/5 rounded-2xl p-8 mb-8">
              <h3 className="text-[10px] font-bold tracking-[0.2em] text-white/40 uppercase mb-4">Discussion Summary</h3>

              <div className="space-y-6">
                <div>
                  <p className="text-white/50 text-sm font-serif italic mb-1">Question</p>
                  <p className="text-lg font-serif italic text-white/90">"{question}"</p>
                </div>

                <div>
                  <p className="text-white/50 text-sm font-serif italic mb-2">Experts ({selected.length})</p>
                  <div className="flex gap-3 flex-wrap">
                    {SYSTEM_PERSONAS.filter((e) => selected.includes(e.id)).map((e) => (
                      <div key={e.id} className="flex items-center gap-2 bg-[#1e2430] rounded-lg px-3 py-2 border border-white/5">
                        <img src={e.avatar} className="w-6 h-6 rounded object-cover" alt={e.name} referrerPolicy="no-referrer" />
                        <span className="text-sm font-medium">{e.name}</span>
                      </div>
                    ))}
                  </div>
                </div>

                <div className="grid grid-cols-3 gap-4 pt-4 border-t border-white/10">
                  <div>
                    <p className="text-white/50 text-xs font-serif italic mb-1">Model</p>
                    <p className="text-sm font-bold">{LLM_MODELS.find(m => m.value === model)?.label ?? model}</p>
                  </div>
                  <div>
                    <p className="text-white/50 text-xs font-serif italic mb-1">Max Rounds</p>
                    <p className="text-sm font-bold">{maxRounds}</p>
                  </div>
                  <div>
                    <p className="text-white/50 text-xs font-serif italic mb-1">Token Budget</p>
                    <p className="text-sm font-bold">{(tokenBudget / 1000).toFixed(0)}K</p>
                  </div>
                </div>
              </div>
            </div>

            <div className="flex gap-4">
              <button
                onClick={() => setStep(2)}
                className="flex items-center gap-2 px-6 py-3 bg-[#151a23] text-white/70 font-bold rounded-xl border border-white/10 hover:bg-white/5 transition-colors"
              >
                <ArrowLeft className="w-4 h-4" /> Back
              </button>
              <button
                onClick={handleStart}
                disabled={launching}
                className="flex-1 py-4 bg-[#00e5ff] hover:bg-[#00cce6] text-black font-bold font-sans rounded-xl transition-colors shadow-[0_0_20px_rgba(0,229,255,0.3)] disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {launching ? '启动中...' : '🚀 START DISCUSSION'}
              </button>
            </div>
            {error && (
              <div className="mt-4 bg-red-500/10 border border-red-500/20 text-red-400 text-sm rounded-lg px-4 py-3">
                {error}
              </div>
            )}
            <p className="text-center text-xs text-white/40 font-serif italic mt-4">Estimated sync time: ~12 seconds</p>
          </motion.div>
        )}
      </div>
    </div>
  );
}
