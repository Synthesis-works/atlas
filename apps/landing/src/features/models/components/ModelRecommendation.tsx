import React, { useState } from 'react';
import { Trophy, Code, MessageSquare, Eye, FileText, CheckCircle, ArrowRight, DollarSign, Zap, Shield } from 'lucide-react';
import { useModelsStore } from '../store/modelsStore';

interface WorkloadCard {
  id: string;
  category: string;
  icon: React.ComponentType<{ className?: string }>;
  winner: string;
  provider: string;
  costTier: string;
  latencyMs: number;
  accuracy: number;
  oneSentenceRationale: string;
  reasons: string[];
  recommendedModelId: string;
}

const WORKLOADS: WorkloadCard[] = [
  {
    id: 'coding',
    category: 'Coding & Agent Assistant',
    icon: Code,
    winner: 'Claude 3.5 Sonnet',
    provider: 'Anthropic',
    costTier: '$$$',
    latencyMs: 142,
    accuracy: 94.8,
    oneSentenceRationale: 'Recommended because it achieves the highest coding accuracy and lowest hallucination rate on complex multi-file software engineering tasks.',
    reasons: [
      'Highest coding accuracy on HumanEval & SWE-bench (92.4%)',
      'Lowest hallucination rate on multi-file code synthesis',
      'Native function calling and agent tool use optimization',
    ],
    recommendedModelId: 'claude-3-5-sonnet',
  },
  {
    id: 'support',
    category: 'Customer Support & Chat',
    icon: MessageSquare,
    winner: 'GPT-5 Mini',
    provider: 'OpenAI',
    costTier: '$',
    latencyMs: 82,
    accuracy: 89.2,
    oneSentenceRationale: 'Recommended because it delivers the lowest response latency (82ms p90) while maintaining high instruction-following quality for high-volume chat.',
    reasons: [
      'Ultra-fast response latency (82ms p90)',
      'Extremely low unit cost ($0.0015 / 1k tokens)',
      'High instruction-following reliability under load',
    ],
    recommendedModelId: 'gpt-4o-mini',
  },
  {
    id: 'vision',
    category: 'Vision & OCR Document Extract',
    icon: Eye,
    winner: 'Gemini 2.0 Flash',
    provider: 'Google',
    costTier: '$',
    latencyMs: 98,
    accuracy: 91.5,
    oneSentenceRationale: 'Recommended because it processes multi-page PDF documents and images 22% cheaper with sub-100ms extraction speeds.',
    reasons: [
      'Native multimodal vision engine (98.2% OCR precision)',
      '22% cheaper than competing vision models',
      'Sub-100ms multi-page PDF processing',
    ],
    recommendedModelId: 'gemini-1-5-flash',
  },
  {
    id: 'long-context',
    category: 'Long Context & Document Search',
    icon: FileText,
    winner: 'Qwen 2.5 72B',
    provider: 'Alibaba / Open-Source',
    costTier: '$$',
    latencyMs: 165,
    accuracy: 92.1,
    oneSentenceRationale: 'Recommended because it offers a 128k token context window with zero recall drop and full self-hosted data privacy on vLLM nodes.',
    reasons: [
      '128k token context window with zero recall drop',
      'Self-hosted vLLM deployment option for full data privacy',
      'Superior structured JSON output compliance',
    ],
    recommendedModelId: 'qwen-2-5-72b',
  },
];

export const ModelRecommendation: React.FC = () => {
  const { openDrawer, models } = useModelsStore();
  const [selectedId, setSelectedId] = useState('coding');

  const activeWorkload = WORKLOADS.find((w) => w.id === selectedId) || WORKLOADS[0];

  const handleDeployRecommendation = (modelName: string) => {
    const matched = models.find((m) => m.name.toLowerCase().includes(modelName.toLowerCase().split(' ')[0]));
    if (matched) openDrawer(matched, 'overview');
  };

  return (
    <div className="liquid-glass-card rounded-2xl p-5 sm:p-6 border border-white/10 space-y-5">
      {/* Section Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-b border-white/[0.06] pb-4">
        <div>
          <div className="flex items-center gap-2 font-mono text-xs text-accent uppercase tracking-wider mb-1">
            <Trophy className="w-4 h-4 text-amber-400" />
            <span>Pillar 2: Model Intelligence Decision Engine</span>
          </div>
          <h2 className="text-lg font-bold text-white tracking-tight">Workload Recommendations & Trade-Off Analysis</h2>
          <p className="text-xs text-white/40 mt-0.5">
            Picks the optimal production model per use-case based on accuracy, latency, and cost efficiency.
          </p>
        </div>

        {/* Category Tabs */}
        <div className="flex items-center gap-1 bg-white/5 p-1 rounded-xl border border-white/5 overflow-x-auto scrollbar-none shrink-0">
          {WORKLOADS.map((w) => {
            const Icon = w.icon;
            return (
              <button
                key={w.id}
                onClick={() => setSelectedId(w.id)}
                className={`px-3 py-1.5 rounded-lg text-xs font-mono transition-all flex items-center gap-1.5 cursor-pointer whitespace-nowrap ${
                  selectedId === w.id
                    ? 'bg-white/10 text-white font-semibold border border-white/15 shadow-sm'
                    : 'text-white/40 hover:text-white/70'
                }`}
              >
                <Icon className="w-3.5 h-3.5" />
                <span>{w.category.split('&')[0]}</span>
              </button>
            );
          })}
        </div>
      </div>

      {/* Recommended Winner Showcase Card */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-5 items-stretch">
        {/* Left: Champion Model Box */}
        <div className="p-5 rounded-2xl border border-amber-500/30 bg-amber-950/20 backdrop-blur-md flex flex-col justify-between space-y-4">
          <div>
            <div className="flex items-center justify-between">
              <span className="px-2.5 py-0.5 rounded-full text-[10px] font-mono font-bold uppercase tracking-wider bg-amber-500/20 text-amber-300 border border-amber-500/30 flex items-center gap-1">
                <Trophy className="w-3 h-3 text-amber-400" /> Recommended Winner
              </span>
              <span className="text-xs font-mono text-white/40">{activeWorkload.provider}</span>
            </div>

            <h3 className="text-xl font-bold text-white mt-3 font-mono">{activeWorkload.winner}</h3>
            <p className="text-xs text-white/50 mt-1">{activeWorkload.category}</p>
          </div>

          <div className="grid grid-cols-3 gap-2 py-3 border-y border-white/10 text-center font-mono">
            <div>
              <div className="text-[10px] text-white/40 uppercase">Accuracy</div>
              <div className="text-sm font-bold text-emerald-400 mt-0.5">{activeWorkload.accuracy}%</div>
            </div>
            <div>
              <div className="text-[10px] text-white/40 uppercase">p90 Latency</div>
              <div className="text-sm font-bold text-blue-400 mt-0.5">{activeWorkload.latencyMs}ms</div>
            </div>
            <div>
              <div className="text-[10px] text-white/40 uppercase">Cost Tier</div>
              <div className="text-sm font-bold text-amber-300 mt-0.5">{activeWorkload.costTier}</div>
            </div>
          </div>

          <button
            onClick={() => handleDeployRecommendation(activeWorkload.winner)}
            className="w-full flex items-center justify-center gap-2 py-2.5 px-4 rounded-xl bg-amber-400 text-neutral-950 font-semibold text-xs hover:bg-amber-300 transition-colors cursor-pointer"
          >
            <span>Deploy Recommended Endpoint</span>
            <ArrowRight className="w-3.5 h-3.5" />
          </button>
        </div>

        {/* Middle & Right: One-Sentence Human Rationale & Benchmark Evidence */}
        <div className="lg:col-span-2 p-5 rounded-2xl border border-white/10 bg-white/[0.02] flex flex-col justify-between space-y-4">
          <div>
            <div className="p-3.5 rounded-xl border border-amber-500/20 bg-amber-500/5 mb-4">
              <div className="text-[10px] font-mono uppercase tracking-wider text-amber-400 font-bold mb-1">
                AI Executive Recommendation Rationale
              </div>
              <p className="text-xs text-white/90 font-medium italic leading-relaxed">
                "{activeWorkload.oneSentenceRationale}"
              </p>
            </div>

            <h4 className="text-xs font-mono uppercase tracking-wider text-white/40 font-semibold mb-2.5">
              Benchmark Evidence & Operational Reasons
            </h4>
            <div className="space-y-2">
              {activeWorkload.reasons.map((reason, idx) => (
                <div key={idx} className="flex items-start gap-2 text-xs text-white/80 font-sans">
                  <CheckCircle className="w-4 h-4 text-emerald-400 shrink-0 mt-0.5" />
                  <span>{reason}</span>
                </div>
              ))}
            </div>
          </div>

          {/* Trade-off Bar Indicators */}
          <div className="pt-3 border-t border-white/5 space-y-2 font-mono text-xs">
            <div className="text-[10px] uppercase text-white/40 tracking-wider">Fleet Trade-off Spectrum</div>
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
              <div className="p-2.5 rounded-xl border border-white/5 bg-white/[0.02] space-y-1">
                <div className="flex items-center justify-between text-[10px] text-white/40">
                  <span>Accuracy Index</span>
                  <Shield className="w-3 h-3 text-emerald-400" />
                </div>
                <div className="text-sm font-bold text-white">{activeWorkload.accuracy}/100</div>
              </div>

              <div className="p-2.5 rounded-xl border border-white/5 bg-white/[0.02] space-y-1">
                <div className="flex items-center justify-between text-[10px] text-white/40">
                  <span>Inference Speed</span>
                  <Zap className="w-3 h-3 text-blue-400" />
                </div>
                <div className="text-sm font-bold text-white">{activeWorkload.latencyMs} ms</div>
              </div>

              <div className="p-2.5 rounded-xl border border-white/5 bg-white/[0.02] space-y-1">
                <div className="flex items-center justify-between text-[10px] text-white/40">
                  <span>Cost Efficiency</span>
                  <DollarSign className="w-3 h-3 text-amber-400" />
                </div>
                <div className="text-sm font-bold text-white">{activeWorkload.costTier} Tier</div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
