import React, { useState } from 'react';
import { DraggableCardBody } from '@/components/ui/draggable-card';
import { GlassGlow } from '@/design/glass/GlassGlow';
import { Cpu, Send, RefreshCw } from 'lucide-react';

export function InteractiveSandbox() {
  const [prompt, setPrompt] = useState('');
  const [evaluating, setEvaluating] = useState(false);
  const [scores, setScores] = useState({ coding: 88, reasoning: 82, math: 74 });
  const [glow, setGlow] = useState(false);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!prompt.trim() || evaluating) return;

    setEvaluating(true);
    setTimeout(() => {
      const length = prompt.length;
      setScores({
        coding: Math.min(100, 75 + (length % 25)),
        reasoning: Math.min(100, 80 + ((length * 3) % 20)),
        math: Math.min(100, 68 + ((length * 7) % 30)),
      });
      setEvaluating(false);
      setGlow(true);
      setTimeout(() => setGlow(false), 1200);
    }, 1200);
  };

  return (
    <DraggableCardBody
      className="absolute bottom-20 left-12 w-[320px] h-[380px] p-6 flex flex-col justify-between rounded-3xl bg-neutral-900/40 border border-white/[0.08] backdrop-blur-xl shadow-2xl z-20"
    >
      <GlassGlow active={glow} />

      <div>
        <div className="flex items-center justify-between mb-4">
          <div className="flex items-center gap-1.5 px-2.5 py-1 rounded-full border border-indigo-500/20 bg-indigo-500/10 text-indigo-400 text-[10px] font-semibold uppercase tracking-wider">
            <Cpu className="h-3 w-3" />
            <span>Interactive Sandbox</span>
          </div>
          <span className="text-[10px] text-white/30 font-mono">LIVE JUDGE</span>
        </div>

        <h3 className="text-base font-bold text-white tracking-tight">Evaluate Live Prompt</h3>
        <p className="mt-1.5 text-xs text-white/40 leading-relaxed">
          Type a prompt below to see the LLM scoring engine evaluate capabilities in real-time.
        </p>

        <form onSubmit={handleSubmit} className="mt-4 flex gap-1.5">
          <input
            type="text"
            value={prompt}
            onChange={(e) => setPrompt(e.target.value)}
            placeholder="Type a coding prompt..."
            className="flex-1 min-w-0 h-8 px-2.5 text-xs bg-white/[0.03] border border-white/[0.08] rounded-lg outline-none text-white focus:border-indigo-500/40"
            disabled={evaluating}
          />
          <button
            type="submit"
            disabled={!prompt.trim() || evaluating}
            className="h-8 w-8 flex items-center justify-center bg-indigo-500/25 border border-indigo-500/30 text-indigo-300 rounded-lg hover:bg-indigo-500/40 transition-colors disabled:opacity-40 cursor-pointer"
          >
            <Send className="h-3.5 w-3.5" />
          </button>
        </form>
      </div>

      <div>
        {/* Results charts */}
        <div className="space-y-2 border-t border-b border-white/[0.06] py-3.5 mb-4">
          <div>
            <div className="flex justify-between text-[9px] text-white/40 font-mono">
              <span>CODING CAPABILITY</span>
              <span className="font-semibold text-white">{scores.coding}%</span>
            </div>
            <div className="h-1 bg-white/[0.05] rounded-full overflow-hidden mt-1">
              <div
                className="h-full bg-emerald-450 transition-all duration-700"
                style={{ width: `${scores.coding}%` }}
              />
            </div>
          </div>

          <div>
            <div className="flex justify-between text-[9px] text-white/40 font-mono">
              <span>REASONING ACCURACY</span>
              <span className="font-semibold text-white">{scores.reasoning}%</span>
            </div>
            <div className="h-1 bg-white/[0.05] rounded-full overflow-hidden mt-1">
              <div
                className="h-full bg-indigo-400 transition-all duration-700"
                style={{ width: `${scores.reasoning}%` }}
              />
            </div>
          </div>

          <div>
            <div className="flex justify-between text-[9px] text-white/40 font-mono">
              <span>MATHEMATICAL RIGOUR</span>
              <span className="font-semibold text-white">{scores.math}%</span>
            </div>
            <div className="h-1 bg-white/[0.05] rounded-full overflow-hidden mt-1">
              <div
                className="h-full bg-pink-400 transition-all duration-700"
                style={{ width: `${scores.math}%` }}
              />
            </div>
          </div>
        </div>

        <div className="flex justify-between text-[9px] text-white/20 select-none">
          <span className="flex items-center gap-1">
            <RefreshCw className={`h-2.5 w-2.5 ${evaluating ? 'animate-spin' : ''}`} />
            {evaluating ? 'Evaluating prompt...' : 'Engine Idle'}
          </span>
          <span>DRAG TO TOSS</span>
        </div>
      </div>
    </DraggableCardBody>
  );
}
