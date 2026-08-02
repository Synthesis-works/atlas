import { Sparkles, AlertTriangle } from 'lucide-react';

export const InsightsEngineCard: React.FC = () => {
  return (
    <div className="p-5 rounded-2xl border border-purple-500/20 bg-purple-950/10 backdrop-blur-md space-y-3">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <div className="w-7 h-7 rounded-lg bg-purple-500/20 border border-purple-500/30 flex items-center justify-center">
            <Sparkles className="w-4 h-4 text-purple-300" />
          </div>
          <div>
            <h3 className="text-xs font-semibold text-white tracking-tight">Atlas AI Insights Engine</h3>
            <p className="text-[10px] font-mono text-purple-300/60">Automated evaluation anomaly detection</p>
          </div>
        </div>
        <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-purple-500/20 text-purple-300 border border-purple-500/30">
          Proactive Diagnostic
        </span>
      </div>

      <div className="p-3.5 rounded-xl border border-purple-500/10 bg-neutral-950/60 space-y-2 text-xs font-mono">
        <div className="flex items-center gap-2 text-amber-400 font-semibold">
          <AlertTriangle className="w-3.5 h-3.5" />
          <span>Regression Detected in MMLU-Pro (CoT Prompt Revision)</span>
        </div>
        <p className="text-white/70 text-[11px] leading-relaxed">
          Accuracy dropped 4.2% and latency increased by 21% following prompt template update v2.1.0. Likely caused by extended reasoning chains.
        </p>
        <div className="flex items-center gap-3 pt-1 text-[10px] text-purple-300">
          <button className="underline hover:text-white">View Regression Report →</button>
          <button className="underline hover:text-white">Rollback Prompt Template</button>
        </div>
      </div>
    </div>
  );
};

export default InsightsEngineCard;
