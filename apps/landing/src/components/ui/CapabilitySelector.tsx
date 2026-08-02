import { useState, type RefObject } from 'react';
import { DraggableCardBody } from '@/components/ui/draggable-card';
import { GlassGlow } from '@/design/glass/GlassGlow';
import { BarChart3 } from 'lucide-react';

export function CapabilitySelector({
  boundsRef,
}: {
  boundsRef?: RefObject<HTMLElement | null>;
}) {
  const [selected, setSelected] = useState<string | null>('Reasoning');
  const [glow, setGlow] = useState(false);

  const comparisonData: Record<string, { gpt: string; claude: string; openWeights: string }> = {
    Reasoning: { gpt: '94.2%', claude: '92.6%', openWeights: '78.1%' },
    Coding: { gpt: '92.8%', claude: '94.6%', openWeights: '81.4%' },
    Mathematics: { gpt: '89.5%', claude: '87.1%', openWeights: '75.2%' },
  };

  const handleSelect = (cap: string) => {
    setSelected(cap);
    setGlow(true);
    setTimeout(() => setGlow(false), 800);
  };

  return (
    <DraggableCardBody
      dragBoundsRef={boundsRef}
      className="w-full h-full min-h-[360px] p-6 flex flex-col justify-between rounded-2xl bg-neutral-900/40 border border-white/[0.08] backdrop-blur-xl shadow-2xl"
    >
      <GlassGlow active={glow} duration={800} />

      <div>
        <div className="flex items-center justify-between mb-4">
          <div className="flex items-center gap-1.5 px-2.5 py-1 rounded-full border border-indigo-500/20 bg-indigo-500/10 text-indigo-400 text-[10px] font-semibold uppercase tracking-wider">
            <BarChart3 className="h-3 w-3" />
            <span>Capability Selector</span>
          </div>
          <span className="text-[10px] text-white/30 font-mono">COMPARATOR</span>
        </div>

        <h3 className="text-base font-bold text-white tracking-tight">Compare Model Strengths</h3>
        <p className="mt-1.5 text-xs text-white/40 leading-relaxed">
          Select capability tags below to run cross-model scoring matrix comparisons.
        </p>

        {/* Selector Toggles */}
        <div className="mt-4 flex flex-col gap-2">
          {Object.keys(comparisonData).map((cap) => (
            <button
              key={cap}
              onClick={() => handleSelect(cap)}
              className={`w-full py-2 px-3 flex items-center justify-between border rounded-xl text-xs font-semibold tracking-wide transition-all cursor-pointer ${
                selected === cap
                  ? 'bg-indigo-500/15 border-indigo-500/45 text-indigo-300'
                  : 'bg-white/[0.02] border-white/[0.04] text-white/50 hover:text-white/80 hover:bg-white/[0.05]'
              }`}
            >
              <span>{cap} Benchmarks</span>
              <span className="text-[10px] text-white/20 uppercase tracking-widest font-mono">Select</span>
            </button>
          ))}
        </div>
      </div>

      {/* Comparison results */}
      {selected ? (
        <div className="bg-white/[0.02] border border-white/[0.06] rounded-2xl p-4 space-y-2.5">
          <div className="flex justify-between text-[10px] border-b border-white/[0.04] pb-1.5">
            <span className="text-white/35 font-mono">MODEL</span>
            <span className="text-white/35 font-mono">BENCHMARK SCORE</span>
          </div>
          <div className="flex justify-between text-xs font-semibold text-white">
            <span>GPT-5 Intel</span>
            <span className="text-indigo-400">{comparisonData[selected].gpt}</span>
          </div>
          <div className="flex justify-between text-xs font-semibold text-white">
            <span>Claude 3.5 Sonnet</span>
            <span className="text-pink-400">{comparisonData[selected].claude}</span>
          </div>
          <div className="flex justify-between text-xs font-semibold text-white">
            <span>Gemma 2 27B</span>
            <span className="text-cyan-400">{comparisonData[selected].openWeights}</span>
          </div>
        </div>
      ) : (
        <div className="bg-white/[0.02] border border-white/[0.04] rounded-2xl p-4 py-8 text-center text-xs text-white/35">
          Choose a capability node to view cross-benchmark capabilities.
        </div>
      )}

      <div className="flex justify-between text-[9px] text-white/20 select-none">
        <span>Stiffness: 100 · Snap size: 40px</span>
        <span>DRAG TO TOSS</span>
      </div>
    </DraggableCardBody>
  );
}
