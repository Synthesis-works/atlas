
import { ShieldAlert, Check, X } from 'lucide-react';
import { motion } from 'framer-motion';
import { STATUS_TONES } from '@/features/agent/status';

interface ApprovalProps {
  message: string;
  onApprove: () => void;
  onReject: () => void;
}

export function AgentApprovalCard({ message, onApprove, onReject }: ApprovalProps) {
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
          <ShieldAlert className="w-5 h-5" />
        </div>
        <div>
          <p className={`text-[10px] uppercase tracking-wider font-bold ${attention.text} flex items-center gap-1.5`}>
            <span className="w-1.5 h-1.5 rounded-full bg-amber-400 animate-pulse" />
            Action Required
          </p>
          <h3 className="text-lg font-semibold text-white">Permission Required</h3>
          <p className="text-xs text-white/50">Atlas requires authorization for this action</p>
        </div>
      </div>

      <div className="bg-white/[0.03] rounded-xl p-5 border border-white/5 mb-6 text-white/90 leading-relaxed text-sm font-mono">
        {message}
      </div>

      <div className="flex gap-4">
        <button
          onClick={onApprove}
          className="flex-1 flex items-center justify-center gap-2 px-4 py-2.5 rounded-lg bg-emerald-500/20 hover:bg-emerald-500/30 border border-emerald-500/40 text-emerald-400 font-medium transition-colors"
        >
          <Check className="w-4 h-4" />
          Approve Action
        </button>
        
        <button
          onClick={onReject}
          className="flex-1 flex items-center justify-center gap-2 px-4 py-2.5 rounded-lg bg-white/5 hover:bg-white/10 border border-white/10 text-white/70 hover:text-white transition-colors"
        >
          <X className="w-4 h-4" />
          Deny & Cancel
        </button>
      </div>
    </motion.div>
  );
}
