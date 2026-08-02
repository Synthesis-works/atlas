import React, { useState } from 'react';
import { GlassGlow } from '@/design/glass/GlassGlow';
import { Calculator, DollarSign } from 'lucide-react';

export function CostEstimator() {
  const [tokens, setTokens] = useState(10);
  const [modelType, setModelType] = useState<'tier1' | 'tier2' | 'tier3'>('tier2');
  const [glow, setGlow] = useState(false);

  const getRate = () => {
    if (modelType === 'tier1') return 0.50;
    if (modelType === 'tier2') return 3.00;
    return 15.00;
  };

  const calculatedCost = tokens * getRate() * 1.25;

  const handleSliderChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    setTokens(Number(e.target.value));
    setGlow(true);
    const timer = setTimeout(() => setGlow(false), 800);
    return () => clearTimeout(timer);
  };

  return (
    <div className="w-full p-6 flex flex-col justify-between rounded-2xl bg-neutral-900/40 border border-white/[0.08] backdrop-blur-xl shadow-2xl">
      <GlassGlow active={glow} duration={800} />

      <div>
        <div className="flex items-center justify-between mb-4">
          <div className="flex items-center gap-1.5 px-2.5 py-1 rounded-full border border-indigo-500/20 bg-indigo-500/10 text-indigo-400 text-[10px] font-semibold uppercase tracking-wider">
            <Calculator className="h-3 w-3" />
            <span>Cost Estimator</span>
          </div>
          <span className="text-[10px] text-white/30 font-mono">CALCULATOR</span>
        </div>

        <h3 className="text-base font-bold text-white tracking-tight">Monthly Budget Calculator</h3>
        <p className="mt-1.5 text-xs text-white/40 leading-relaxed">
          Estimate cluster run costs based on token scale and judge tiers.
        </p>

        {/* Model Tiers */}
        <div className="mt-4 flex gap-1.5">
          {(['tier1', 'tier2', 'tier3'] as const).map((tier) => (
            <button
              key={tier}
              type="button"
              onClick={() => {
                setModelType(tier);
                setGlow(true);
                setTimeout(() => setGlow(false), 800);
              }}
              className={`flex-1 py-1.5 text-[9px] font-semibold border rounded-lg transition-all cursor-pointer ${
                modelType === tier
                  ? 'bg-indigo-500/15 border-indigo-500/45 text-indigo-300'
                  : 'bg-white/[0.02] border-white/[0.04] text-white/40 hover:text-white/70'
              }`}
            >
              {tier === 'tier1' ? 'Local LLM' : tier === 'tier2' ? 'Frontier' : 'GPT-5 Intel'}
            </button>
          ))}
        </div>
      </div>

      {/* Slider */}
      <div className="space-y-2">
        <div className="flex justify-between text-xs text-white/50">
          <span>Evaluated Volume</span>
          <span className="font-semibold text-white">{tokens}M tokens</span>
        </div>
        <input
          type="range"
          min="1"
          max="100"
          value={tokens}
          onChange={handleSliderChange}
          className="w-full h-1 bg-white/[0.08] rounded-lg appearance-none cursor-pointer accent-indigo-500"
        />
      </div>

      {/* Result Display */}
      <div className="bg-white/[0.02] border border-white/[0.06] rounded-2xl p-4 flex items-center justify-between">
        <div>
          <span className="text-[10px] text-white/20 uppercase tracking-widest font-mono">ESTIMATED RUNS</span>
          <div className="flex items-baseline gap-0.5 mt-0.5">
            <DollarSign className="h-4 w-4 text-emerald-400" />
            <span className="text-2xl font-black text-white">{calculatedCost.toFixed(2)}</span>
            <span className="text-[10px] text-white/30 ml-1">/ mo</span>
          </div>
        </div>
        <div className="text-right text-[9px] text-white/20 leading-tight">
          Includes 25%<br />Judge surcharge
        </div>
      </div>

      <div className="flex justify-between text-[9px] text-white/20 select-none">
        <span>Stiffness: 100 · Damping: 20</span>
        <span>DRAG TO TOSS</span>
      </div>
    </div>
  );
}
