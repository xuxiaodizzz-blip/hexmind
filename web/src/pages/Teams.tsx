import { motion } from 'motion/react';
import { Users } from 'lucide-react';
import { useLanguage } from '../hooks/useLanguage';

export default function Teams() {
  const { t } = useLanguage();

  return (
    <div className="flex-1 overflow-y-auto no-scrollbar p-8 lg:p-12 z-10 w-full bg-[#0b0f17] text-white">
      <div className="max-w-4xl mx-auto">
        <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} className="mb-10">
          <h1 className="text-4xl font-bold font-sans mb-2 tracking-tight">{t('teams.title')}</h1>
          <p className="text-white/50 font-serif italic text-lg">{t('teams.subtitle')}</p>
        </motion.div>

        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.1 }}
          className="rounded-3xl border border-white/5 bg-[#151a23] p-10 md:p-12"
        >
          <div className="w-16 h-16 rounded-2xl bg-[#00e5ff]/10 border border-[#00e5ff]/20 flex items-center justify-center mb-6">
            <Users className="w-8 h-8 text-[#00e5ff]" />
          </div>
          <h2 className="text-2xl font-bold font-sans mb-3">{t('teams.emptyTitle')}</h2>
          <p className="max-w-2xl text-white/50 font-serif italic leading-relaxed">
            {t('teams.emptyBody')}
          </p>
        </motion.div>
      </div>
    </div>
  );
}
