import React from 'react';
import { Sparkles, TrendingUp, AlertTriangle, CheckCircle, Zap } from 'lucide-react';

const INSIGHTS = [
  {
    id: 1,
    severity: 'ALERT',
    badgeText: '🚨 VRAM Saturation',
    text: 'Claude 3.5 Sonnet deployment approaching saturation (88% GPU VRAM).',
    icon: AlertTriangle,
    color: 'text-rose-300 border-rose-500/30 bg-rose-950/20 shadow-[0_0_15px_rgba(244,63,94,0.1)]',
  },
  {
    id: 2,
    severity: 'WARNING',
    badgeText: '⚠ Usage Spike',
    text: 'GPU utilization increased 18% today across us-east-1 cluster.',
    icon: TrendingUp,
    color: 'text-amber-300 border-amber-500/30 bg-amber-950/20 shadow-[0_0_15px_rgba(245,158,11,0.1)]',
  },
  {
    id: 3,
    severity: 'OPTIMIZATION',
    badgeText: '💲 Cost Savings',
    text: 'Gemini Flash is 22% cheaper for Vision & OCR workloads.',
    icon: Sparkles,
    color: 'text-purple-300 border-purple-500/30 bg-purple-950/20 shadow-[0_0_15px_rgba(168,85,247,0.1)]',
  },
  {
    id: 4,
    severity: 'INFO',
    badgeText: '⚡ Traffic Share',
    text: 'GPT-5 Mini handles 46% of all incoming production traffic.',
    icon: Zap,
    color: 'text-blue-300 border-blue-500/30 bg-blue-950/20 shadow-[0_0_15px_rgba(59,130,246,0.1)]',
  },
  {
    id: 5,
    severity: 'SUCCESS',
    badgeText: '✓ Latency Improved',
    text: 'Llama-3.3 latency improved by 42ms after replica scale to 4 pods.',
    icon: CheckCircle,
    color: 'text-emerald-300 border-emerald-500/30 bg-emerald-950/20 shadow-[0_0_15px_rgba(16,185,129,0.1)]',
  },
];

export const FleetInsights: React.FC = () => {
  return (
    <div className="liquid-glass-card rounded-2xl p-4 sm:p-5 border border-white/10 space-y-3">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2 font-mono text-xs text-white/80 font-semibold">
          <Sparkles className="w-4 h-4 text-purple-400" />
          <span>AI Fleet Insights & Operational Intelligence</span>
        </div>
        <span className="text-[10px] font-mono text-white/30 uppercase tracking-wider">
          Severity-Categorized AI Diagnostics
        </span>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-5 gap-3">
        {INSIGHTS.map((item) => {
          const Icon = item.icon;
          return (
            <div
              key={item.id}
              className={`p-3 rounded-xl border flex flex-col justify-between space-y-2 font-mono text-xs transition-all hover:border-white/30 ${item.color}`}
            >
              <div className="flex items-center justify-between gap-2">
                <span className="text-[9px] uppercase font-bold tracking-wider px-1.5 py-0.5 rounded bg-black/30 border border-white/10">
                  {item.badgeText}
                </span>
                <Icon className="w-3.5 h-3.5 shrink-0" />
              </div>
              <p className="text-white/90 leading-snug font-sans text-xs font-medium">{item.text}</p>
            </div>
          );
        })}
      </div>
    </div>
  );
};
