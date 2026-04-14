import { useState } from 'react';
import { motion } from 'motion/react';
import { Link, useNavigate } from 'react-router-dom';
import { Hexagon } from 'lucide-react';
import * as api from '../lib/api';

export default function Login() {
  const navigate = useNavigate();
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    setLoading(true);
    try {
      await api.login(email, password);
      navigate('/app');
    } catch (err) {
      setError(err instanceof api.ApiError ? err.message : '登录失败，请重试');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="h-full overflow-y-auto no-scrollbar bg-[#0b0f17] text-white flex items-center justify-center relative">
      {/* Background Effects */}
      <div className="absolute top-0 left-0 w-full h-full overflow-hidden pointer-events-none">
        <div className="absolute top-[-20%] left-[-20%] w-[50%] h-[50%] bg-[#00e5ff]/5 rounded-full blur-[120px]" />
        <div className="absolute bottom-[-20%] right-[-20%] w-[50%] h-[50%] bg-[#b499ff]/5 rounded-full blur-[120px]" />
      </div>

      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        className="relative z-10 w-full max-w-md px-6"
      >
        {/* Logo */}
        <Link to="/" className="flex items-center gap-3 justify-center mb-12">
          <div className="w-12 h-12 rounded-xl bg-[#00e5ff]/10 flex items-center justify-center border border-[#00e5ff]/20 shadow-[0_0_15px_rgba(0,229,255,0.1)]">
            <Hexagon className="text-[#00e5ff] w-7 h-7" />
          </div>
          <div>
            <h1 className="text-2xl font-bold tracking-tight text-white leading-tight">HexMind</h1>
            <p className="text-[9px] font-serif italic text-white/50 tracking-widest uppercase">The Ethereal Archive</p>
          </div>
        </Link>

        <div className="bg-[#151a23] border border-white/5 rounded-2xl p-8 shadow-lg">
          <h2 className="text-2xl font-bold font-sans mb-2 text-center">Welcome Back</h2>
          <p className="text-white/50 font-serif italic text-sm text-center mb-8">Enter the Archive</p>

          <form onSubmit={handleSubmit} className="space-y-5">
            {error && (
              <div className="bg-red-500/10 border border-red-500/20 text-red-400 text-sm rounded-lg px-4 py-3">
                {error}
              </div>
            )}
            <div>
              <label className="block text-[10px] font-bold tracking-[0.15em] text-white/50 uppercase mb-2">Email</label>
              <input
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="your@email.com"
                className="w-full bg-[#1e2430] border border-white/10 rounded-xl px-4 py-3 text-sm text-white placeholder:text-white/30 focus:outline-none focus:border-[#00e5ff]/50 transition-colors"
                required
              />
            </div>
            <div>
              <label className="block text-[10px] font-bold tracking-[0.15em] text-white/50 uppercase mb-2">Password</label>
              <input
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="••••••••"
                className="w-full bg-[#1e2430] border border-white/10 rounded-xl px-4 py-3 text-sm text-white placeholder:text-white/30 focus:outline-none focus:border-[#00e5ff]/50 transition-colors"
                required
              />
            </div>
            <button
              type="submit"
              disabled={loading}
              className="w-full bg-[#00e5ff] hover:bg-[#00cce6] text-black font-bold py-3.5 rounded-xl transition-colors shadow-[0_0_20px_rgba(0,229,255,0.2)] disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {loading ? '登录中...' : 'Sign In'}
            </button>
          </form>

          {/* OAuth Placeholder */}
          <div className="mt-6 pt-6 border-t border-white/5 space-y-3">
            <button disabled className="w-full bg-[#1e2430] border border-white/5 text-white/30 py-3 rounded-xl text-sm font-medium cursor-not-allowed">
              Continue with Google — Coming Soon
            </button>
            <button disabled className="w-full bg-[#1e2430] border border-white/5 text-white/30 py-3 rounded-xl text-sm font-medium cursor-not-allowed">
              Continue with GitHub — Coming Soon
            </button>
          </div>

          <p className="text-center text-sm text-white/40 mt-6">
            Don't have an account?{' '}
            <Link to="/register" className="text-[#00e5ff] hover:underline">
              Create one
            </Link>
          </p>
        </div>
      </motion.div>
    </div>
  );
}
