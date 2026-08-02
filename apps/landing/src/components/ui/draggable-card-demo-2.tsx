/**
 * DraggableCardDemo — Atlas Interactive Sandbox demo
 *
 * Fixes:
 * - Cards now use absolute positioning correctly inside the relative container
 * - Removed conflicting layout classes from DraggableCardBody className
 * - Status dot colors use inline styles to avoid Tailwind purge issues
 */

import {
  DraggableCardBody,
  DraggableCardContainer,
} from '@/components/ui/draggable-card';
import { Cpu, ShieldCheck, Database, Award } from 'lucide-react';

const STATUS_DOT: Record<string, string> = {
  Running:   '#818cf8',   // indigo
  Completed: '#34d399',   // emerald
  Queued:    '#fbbf24',   // amber
  Failed:    '#f87171',   // red
};

const ATLAS_ITEMS = [
  {
    title: 'GPT-5 Evaluation',
    category: 'Models',
    icon: <Cpu className="h-3.5 w-3.5 text-indigo-400" />,
    colorClass: 'text-indigo-400 bg-indigo-500/10 border-indigo-500/20',
    metrics: { MMLU: '92.8%', Latency: '120ms', Memory: '32GB' },
    description: 'In-flight capabilities testing for general reasoning and math proficiency.',
    style: { top: '8%',  left: '12%', rotate: '-5deg' },
    status: 'Running',
  },
  {
    title: 'Claude 4 Sonnet',
    category: 'Safety',
    icon: <ShieldCheck className="h-3.5 w-3.5 text-pink-400" />,
    colorClass: 'text-pink-400 bg-pink-500/10 border-pink-500/20',
    metrics: { GPQA: '81.2%', 'Red Team': '99.1%', Latency: '185ms' },
    description: 'Safety bounds alignment checks against adversarial exploit scripts.',
    style: { top: '36%', left: '6%',  rotate: '-2deg' },
    status: 'Completed',
  },
  {
    title: 'Gemini 2.5 Pro',
    category: 'Benchmarks',
    icon: <Database className="h-3.5 w-3.5 text-cyan-400" />,
    colorClass: 'text-cyan-400 bg-cyan-500/10 border-cyan-500/20',
    metrics: { 'Arena Hard': '78.5%', 'Pass@1': '88.2%', Latency: '90ms' },
    description: 'Long-context regression checks relative to baseline weights.',
    style: { top: '5%',  left: '40%', rotate: '4deg' },
    status: 'Queued',
  },
  {
    title: 'Qwen 2.5 Coder',
    category: 'Capabilities',
    icon: <Award className="h-3.5 w-3.5 text-emerald-400" />,
    colorClass: 'text-emerald-400 bg-emerald-500/10 border-emerald-500/20',
    metrics: { HumanEval: '94.6%', SWEbench: '38.5%', Latency: '110ms' },
    description: 'Multi-agent coding task resolution benchmarks.',
    style: { top: '32%', left: '56%', rotate: '6deg' },
    status: 'Completed',
  },
];

export default function DraggableCardDemo() {
  return (
    <DraggableCardContainer className="relative flex min-h-screen w-full items-center justify-center overflow-hidden bg-neutral-950/20">

      {/* Background vignette */}
      <div className="pointer-events-none absolute inset-0 z-0 bg-gradient-to-b from-neutral-950/60 via-transparent to-neutral-950/80" />

      {/* Hero copy */}
      <div className="pointer-events-none absolute inset-x-0 top-[14%] z-10 mx-auto max-w-lg select-none px-4 text-center">
        <h2 className="text-3xl font-bold leading-tight tracking-tight text-white md:text-5xl">
          Atlas Interactive Sandbox
        </h2>
        <p className="mx-auto mt-3 max-w-sm text-xs leading-relaxed text-white/40 md:text-sm">
          Drag and toss model evaluation cards to explore the Liquid Glass physics.
        </p>
      </div>

      {/* Cards — absolutely positioned within the container */}
      {ATLAS_ITEMS.map((item) => (
        <DraggableCardBody
          key={item.title}
          className="absolute w-72 min-h-[340px] p-5 flex flex-col justify-between bg-neutral-900/50 border border-white/[0.08] backdrop-blur-xl shadow-2xl"
          style={{
            top:       item.style.top,
            left:      item.style.left,
            transform: `rotate(${item.style.rotate})`,
          } as React.CSSProperties}
        >
          {/* Card header */}
          <div>
            <div className="mb-4 flex items-center justify-between">
              <div className={`inline-flex items-center gap-1.5 rounded-full border px-2.5 py-1 text-[10px] font-semibold uppercase tracking-wider ${item.colorClass}`}>
                {item.icon}
                <span>{item.category}</span>
              </div>
              <span className="font-mono text-[10px] text-white/25">v1.4</span>
            </div>
            <h3 className="text-base font-bold tracking-tight text-white">{item.title}</h3>
            <p className="mt-2 text-xs leading-relaxed text-white/40">{item.description}</p>
          </div>

          {/* Metrics + status */}
          <div>
            <div className="mb-4 grid grid-cols-3 gap-2 border-y border-white/[0.06] py-3">
              {Object.entries(item.metrics).map(([key, val]) => (
                <div key={key} className="text-center">
                  <span className="block text-[8px] uppercase tracking-wider text-white/30">{key}</span>
                  <span className="mt-0.5 block text-xs font-semibold text-white">{val}</span>
                </div>
              ))}
            </div>

            <div className="flex items-center justify-between text-xs text-white/45">
              <span className="flex items-center gap-1.5">
                <span
                  className="inline-block h-1.5 w-1.5 rounded-full"
                  style={{
                    background: STATUS_DOT[item.status] ?? '#a1a1aa',
                    boxShadow: item.status === 'Running'
                      ? `0 0 6px ${STATUS_DOT[item.status]}`
                      : 'none',
                    animation: item.status === 'Running' ? 'pulse 2s infinite' : 'none',
                  }}
                />
                {item.status}
              </span>
              <span className="text-[9px] uppercase tracking-widest text-white/20">Drag to toss</span>
            </div>
          </div>
        </DraggableCardBody>
      ))}
    </DraggableCardContainer>
  );
}
