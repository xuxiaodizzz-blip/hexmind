import { useEffect, useRef, useState } from 'react';
import { motion } from 'motion/react';
import { useParams, Link } from 'react-router-dom';
import { Bell, HelpCircle, StopCircle, Hexagon } from 'lucide-react';
import * as api from '../lib/api';
import { SYSTEM_PERSONAS } from '../data/personas';

interface SSEMessage {
  id: string;
  event: string;
  data: Record<string, unknown>;
}

const statusLabel: Record<string, string> = {
  running: '讨论进行中',
  converged: '已收敛',
  partial: '部分完成',
  cancelled: '已取消',
  error: '出错',
};

export default function Discussion() {
  const { id } = useParams<{ id: string }>();
  const [status, setStatus] = useState<api.DiscussionStatus | null>(null);
  const [messages, setMessages] = useState<SSEMessage[]>([]);
  const [finished, setFinished] = useState(false);
  const feedRef = useRef<HTMLDivElement>(null);

  // Fetch status
  useEffect(() => {
    if (!id) return;
    api.getDiscussionStatus(id).then(setStatus).catch(() => {});
  }, [id]);

  // Connect SSE
  useEffect(() => {
    if (!id) return;
    const es = api.streamDiscussion(id);
    const terminalEvents = ['conclusion', 'discussion_cancelled', 'error'];

    const handler = (e: MessageEvent) => {
      try {
        const data = JSON.parse(e.data);
        const msg: SSEMessage = { id: e.lastEventId, event: (e as unknown as { type: string }).type || 'message', data };
        setMessages((prev) => [...prev, msg]);
      } catch { /* ignore parse errors */ }
    };

    // Listen for each event type
    const eventTypes = [
      'discussion_started', 'blue_hat_decision', 'round_started',
      'panelist_output', 'round_completed', 'validation_result',
      'fork_created', 'sub_conclusion', 'budget_warning',
      'degradation_changed', 'context_compressed', 'conclusion',
      'discussion_cancelled', 'error',
    ];

    for (const evt of eventTypes) {
      es.addEventListener(evt, (e) => {
        try {
          const data = JSON.parse((e as MessageEvent).data);
          setMessages((prev) => [...prev, { id: (e as MessageEvent).lastEventId, event: evt, data }]);
          if (terminalEvents.includes(evt)) {
            setFinished(true);
            es.close();
          }
        } catch { /* ignore */ }
      });
    }

    es.onerror = () => {
      setFinished(true);
      es.close();
    };

    return () => es.close();
  }, [id]);

  // Auto-scroll
  useEffect(() => {
    feedRef.current?.scrollTo({ top: feedRef.current.scrollHeight, behavior: 'smooth' });
  }, [messages]);

  const personaName = (pid: string) => {
    const p = SYSTEM_PERSONAS.find((x) => x.id === pid);
    return p?.name ?? pid;
  };

  return (
    <div className="flex-1 flex flex-col h-full overflow-hidden bg-[#0b0f17] text-white">
      {/* Header */}
      <header className="h-16 border-b border-white/5 flex items-center justify-between px-6 shrink-0 bg-[#0e131d]">
        <div className="flex items-center gap-3">
          <Link to="/app/history">
            <Hexagon className="w-6 h-6 text-[#00e5ff]" />
          </Link>
          <h1 className="text-lg font-bold font-sans italic tracking-wide">
            Discussion #{id?.slice(0, 8)}
          </h1>
          {status && (
            <span className={`text-[10px] font-bold tracking-widest uppercase px-2 py-0.5 rounded ${status.status === 'running' ? 'bg-[#00e5ff]/10 text-[#00e5ff]' : status.status === 'converged' ? 'bg-green-500/10 text-green-400' : 'bg-white/5 text-white/50'}`}>
              {statusLabel[status.status] ?? status.status}
            </span>
          )}
        </div>
        <div className="flex items-center gap-6">
          {status && (
            <div className="flex items-center gap-3">
              <span className="text-[10px] font-bold tracking-widest text-white/50 uppercase">Token</span>
              <div className="flex items-center gap-2">
                <div className="w-32 h-1.5 bg-[#1e2430] rounded-full overflow-hidden">
                  <div
                    className="h-full bg-[#00e5ff] transition-all duration-500"
                    style={{ width: `${Math.min(100, (status.token_used / status.token_budget) * 100)}%` }}
                  />
                </div>
                <span className="text-xs font-bold font-mono">
                  {status.token_used.toLocaleString()} / {status.token_budget.toLocaleString()}
                </span>
              </div>
            </div>
          )}
          <div className="flex items-center gap-4 border-l border-white/10 pl-6">
            <button className="text-white/50 hover:text-white transition-colors"><Bell className="w-5 h-5" /></button>
            <button className="text-white/50 hover:text-white transition-colors"><HelpCircle className="w-5 h-5" /></button>
          </div>
        </div>
      </header>

      {/* Chat Feed */}
      <div ref={feedRef} className="flex-1 overflow-y-auto no-scrollbar p-8 space-y-6">
        {status && (
          <div className="max-w-3xl mx-auto text-center mb-8">
            <p className="font-serif italic text-xl text-white/80 leading-relaxed">"{status.question}"</p>
            <p className="text-white/40 text-sm mt-2">
              专家: {status.personas.map(personaName).join(', ')} · 轮次: {status.rounds_completed}
            </p>
          </div>
        )}

        {messages.map((msg, i) => {
          if (msg.event === 'panelist_output') {
            const pid = msg.data.persona_id as string;
            const content = msg.data.content as string ?? msg.data.text as string ?? JSON.stringify(msg.data);
            return (
              <motion.div key={i} initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} className="flex gap-4 max-w-3xl">
                <div className="shrink-0 flex flex-col items-center gap-2">
                  <div className="w-10 h-10 bg-[#151a23] rounded-xl flex items-center justify-center border border-white/10">
                    <span className="text-sm">{personaName(pid).charAt(0)}</span>
                  </div>
                  <span className="text-[9px] font-bold tracking-widest text-white/50 uppercase">{personaName(pid)}</span>
                </div>
                <div className="flex-1 bg-[#151a23] border border-white/5 rounded-2xl rounded-tl-none p-6">
                  <p className="font-serif text-base text-white/90 leading-relaxed whitespace-pre-wrap">{content}</p>
                </div>
              </motion.div>
            );
          }

          if (msg.event === 'round_started' || msg.event === 'round_completed') {
            const round = msg.data.round as number ?? '?';
            return (
              <div key={i} className="flex justify-center">
                <div className="bg-[#151a23] border border-white/10 rounded-full px-4 py-1.5 flex items-center gap-2">
                  <div className="w-2 h-2 rounded-full bg-[#00e5ff]" />
                  <span className="text-[10px] font-bold tracking-widest text-white/70 uppercase">
                    {msg.event === 'round_started' ? `第 ${round} 轮开始` : `第 ${round} 轮结束`}
                  </span>
                </div>
              </div>
            );
          }

          if (msg.event === 'conclusion') {
            const text = msg.data.summary as string ?? msg.data.conclusion as string ?? JSON.stringify(msg.data);
            return (
              <motion.div key={i} initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} className="max-w-3xl mx-auto">
                <div className="bg-gradient-to-br from-[#151a23] to-[#0e131d] border border-[#00e5ff]/30 rounded-2xl p-8 shadow-[0_0_30px_rgba(0,229,255,0.05)]">
                  <div className="flex items-center gap-2 mb-4">
                    <Hexagon className="w-5 h-5 text-[#00e5ff]" />
                    <span className="text-[10px] font-bold tracking-widest text-[#00e5ff] uppercase">最终结论</span>
                  </div>
                  <p className="font-serif text-lg text-white/90 leading-relaxed whitespace-pre-wrap">{text}</p>
                </div>
              </motion.div>
            );
          }

          if (msg.event === 'blue_hat_decision') {
            const decision = msg.data.decision as string ?? msg.data.message as string ?? '';
            return (
              <div key={i} className="flex justify-center">
                <div className="bg-[#151a23] border border-blue-500/20 rounded-full px-4 py-1.5">
                  <span className="text-[10px] font-bold tracking-widest text-blue-400 uppercase">蓝帽: {decision}</span>
                </div>
              </div>
            );
          }

          if (msg.event === 'budget_warning') {
            return (
              <div key={i} className="flex justify-center">
                <div className="bg-yellow-500/10 border border-yellow-500/20 rounded-full px-4 py-1.5">
                  <span className="text-[10px] font-bold tracking-widest text-yellow-400 uppercase">⚠ 预算警告</span>
                </div>
              </div>
            );
          }

          if (msg.event === 'error' || msg.event === 'discussion_cancelled') {
            const detail = msg.data.message as string ?? msg.data.detail as string ?? msg.event;
            return (
              <div key={i} className="flex justify-center">
                <div className="bg-red-500/10 border border-red-500/20 rounded-lg px-4 py-2">
                  <span className="text-sm text-red-400">{detail}</span>
                </div>
              </div>
            );
          }

          // Other events — show as subtle info
          return (
            <div key={i} className="flex justify-center">
              <span className="text-[10px] text-white/30">[{msg.event}]</span>
            </div>
          );
        })}

        {!finished && messages.length > 0 && (
          <div className="flex justify-center py-4">
            <div className="flex gap-1">
              <motion.div animate={{ opacity: [0.3, 1, 0.3] }} transition={{ repeat: Infinity, duration: 1.5, delay: 0 }} className="w-2 h-2 rounded-full bg-[#00e5ff]" />
              <motion.div animate={{ opacity: [0.3, 1, 0.3] }} transition={{ repeat: Infinity, duration: 1.5, delay: 0.2 }} className="w-2 h-2 rounded-full bg-[#00e5ff]" />
              <motion.div animate={{ opacity: [0.3, 1, 0.3] }} transition={{ repeat: Infinity, duration: 1.5, delay: 0.4 }} className="w-2 h-2 rounded-full bg-[#00e5ff]" />
            </div>
          </div>
        )}

        {finished && (
          <div className="text-center py-4">
            <span className="text-sm text-white/40 font-serif italic">讨论已结束</span>
          </div>
        )}
      </div>

      {/* Stop button */}
      {!finished && (
        <div className="border-t border-white/5 p-4 flex justify-center bg-[#0e131d]">
          <button className="flex items-center gap-2 px-6 py-2 bg-rose-500/10 hover:bg-rose-500/20 text-rose-400 border border-rose-500/20 rounded-xl text-xs font-bold tracking-widest uppercase transition-colors">
            <StopCircle className="w-4 h-4" /> 停止讨论
          </button>
        </div>
      )}
    </div>
  );
}
