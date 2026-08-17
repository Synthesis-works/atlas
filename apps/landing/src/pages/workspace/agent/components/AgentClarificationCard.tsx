import { useState } from 'react';
import { HelpCircle, Send } from 'lucide-react';
import { motion } from 'framer-motion';
import { STATUS_TONES } from '@/features/agent/status';

interface ClarificationProps {
  question: string;
  options?: string[];
  onSubmit: (response: string) => void;
}

export function AgentClarificationCard({ question, options, onSubmit }: ClarificationProps) {
  const [customInput, setCustomInput] = useState('');
  const attention = STATUS_TONES.attention;

  return (
    <motion.div
      initial={{ opacity: 0, scale: 0.95, y: 20 }}
      animate={{ opacity: 1, scale: 1, y: 0 }}
      className={`bg-ink-1/90 backdrop-blur-xl border ${attention.border} rounded-2xl p-6 shadow-[0_20px_50px_rgba(0,0,0,0.5),inset_0_1px_0_rgba(255,255,255,0.1)] w-full max-w-2xl mx-auto`}
    >
      <div className="flex items-center gap-3 mb-4">
        <div
          className={`w-10 h-10 rounded-full ${attention.bg} flex items-center justify-center border ${attention.border} ${attention.text}`}
        >
          <HelpCircle className="w-5 h-5" />
        </div>
        <div>
          <p className={`text-[10px] uppercase tracking-wider font-bold ${attention.text} flex items-center gap-1.5`}>
            <span className="w-1.5 h-1.5 rounded-full bg-amber-400 animate-pulse" />
            Action Required
          </p>
          <h3 className="text-lg font-semibold text-white">I need one decision from you before I continue</h3>
          <p className="text-xs text-white/50">Your answer will steer the rest of this run</p>
        </div>
      </div>

      <div className="bg-white/[0.03] rounded-xl p-5 border border-white/5 mb-6 text-white/90 leading-relaxed text-sm">
        {question}
      </div>

      <div className="flex flex-col gap-3">
        {options && options.length > 0 && (
          <div className="flex flex-wrap gap-2 mb-1">
            {options.map((opt, i) => (
              <button
                key={i}
                onClick={() => onSubmit(opt)}
                className="px-4 py-2 rounded-lg bg-white/5 hover:bg-amber-500/15 border border-white/10 hover:border-amber-500/40 text-sm text-white/80 transition-colors"
              >
                {opt}
              </button>
            ))}
          </div>
        )}

        <div className="flex gap-2">
          <div className="relative flex-1">
            <input
              type="text"
              value={customInput}
              onChange={(e) => setCustomInput(e.target.value)}
              placeholder="Type your answer…"
              className="w-full bg-black/40 border border-white/10 rounded-xl py-3 pl-4 pr-12 text-sm text-white focus:outline-none focus:border-amber-500/50 focus:ring-1 focus:ring-amber-500/50 transition-all"
              onKeyDown={(e) => {
                if (e.key === 'Enter' && customInput.trim()) {
                  onSubmit(customInput.trim());
                }
              }}
            />
            <button
              onClick={() => {
                if (customInput.trim()) onSubmit(customInput.trim());
              }}
              disabled={!customInput.trim()}
              className="absolute right-2 top-1/2 -translate-y-1/2 p-2 rounded-lg text-white/40 hover:text-amber-300 hover:bg-amber-500/10 disabled:opacity-50 transition-colors"
            >
              <Send className="w-4 h-4" />
            </button>
          </div>
          <button
            onClick={() => {
              if (customInput.trim()) onSubmit(customInput.trim());
            }}
            disabled={!customInput.trim()}
            className={`px-5 py-2.5 rounded-xl font-semibold text-sm transition-colors disabled:opacity-50 disabled:cursor-not-allowed ${attention.bg} ${attention.border} border ${attention.text}`}
          >
            Continue
          </button>
        </div>
      </div>
    </motion.div>
  );
}
