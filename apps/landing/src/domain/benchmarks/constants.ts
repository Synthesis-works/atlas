/**
 * Domain — Benchmarks Constants
 * Category labels, status colors, and filter metadata.
 */

import type { BenchmarkCategory, BenchmarkStatus } from './types';

export const BENCHMARK_CATEGORIES: Record<
  BenchmarkCategory,
  { label: string; color: string; bg: string; border: string; description: string }
> = {
  coding: {
    label: 'Coding',
    color: 'text-emerald-400',
    bg: 'bg-emerald-500/10',
    border: 'border-emerald-500/20',
    description: 'Code synthesis, functional correctness, unit test runners',
  },
  reasoning: {
    label: 'Reasoning',
    color: 'text-purple-400',
    bg: 'bg-purple-500/10',
    border: 'border-purple-500/20',
    description: 'Multi-step logical inference and abstract spatial deduction',
  },
  mathematics: {
    label: 'Mathematics',
    color: 'text-blue-400',
    bg: 'bg-blue-500/10',
    border: 'border-blue-500/20',
    description: 'Symbolic math, numerical word problems, theorem proving',
  },
  planning: {
    label: 'Planning',
    color: 'text-cyan-400',
    bg: 'bg-cyan-500/10',
    border: 'border-cyan-500/20',
    description: 'Long-horizon trajectory optimization and goal decomposition',
  },
  tool_use: {
    label: 'Tool Use',
    color: 'text-amber-400',
    bg: 'bg-amber-500/10',
    border: 'border-amber-500/20',
    description: 'API function calling, parameter extraction, agent loops',
  },
  knowledge: {
    label: 'Knowledge',
    color: 'text-indigo-400',
    bg: 'bg-indigo-500/10',
    border: 'border-indigo-500/20',
    description: 'Multitask domain comprehension and academic question answering',
  },
  safety: {
    label: 'Safety',
    color: 'text-rose-400',
    bg: 'bg-rose-500/10',
    border: 'border-rose-500/20',
    description: 'Truthfulness, alignment, toxicity defense, hallucination rate',
  },
  language: {
    label: 'Language',
    color: 'text-teal-400',
    bg: 'bg-teal-500/10',
    border: 'border-teal-500/20',
    description: 'Natural language inference, grammar, commonsense logic',
  },
  vision: {
    label: 'Vision',
    color: 'text-fuchsia-400',
    bg: 'bg-fuchsia-500/10',
    border: 'border-fuchsia-500/20',
    description: 'Multimodal image analysis, chart reading, spatial OCR',
  },
  multimodal: {
    label: 'Multimodal',
    color: 'text-violet-400',
    bg: 'bg-violet-500/10',
    border: 'border-violet-500/20',
    description: 'Cross-modal audio, image, and text reasoning benchmarks',
  },
  agents: {
    label: 'Agents',
    color: 'text-orange-400',
    bg: 'bg-orange-500/10',
    border: 'border-orange-500/20',
    description: 'Autonomous web browsing, OS interaction, tool chains',
  },
};

export const BENCHMARK_STATUS_MAP: Record<
  BenchmarkStatus,
  { label: string; badgeClass: string; dotClass: string }
> = {
  Draft: {
    label: 'Draft',
    badgeClass: 'bg-white/5 text-white/50 border-white/10',
    dotClass: 'bg-white/40',
  },
  Validating: {
    label: 'Validating',
    badgeClass: 'bg-amber-500/10 text-amber-400 border-amber-500/20',
    dotClass: 'bg-amber-400 animate-pulse',
  },
  Ready: {
    label: 'Ready',
    badgeClass: 'bg-blue-500/10 text-blue-400 border-blue-500/20',
    dotClass: 'bg-blue-400',
  },
  Running: {
    label: 'Running',
    badgeClass: 'bg-emerald-500/10 text-emerald-400 border-emerald-500/20',
    dotClass: 'bg-emerald-400 animate-pulse',
  },
  Paused: {
    label: 'Paused',
    badgeClass: 'bg-orange-500/10 text-orange-400 border-orange-500/20',
    dotClass: 'bg-orange-400',
  },
  Completed: {
    label: 'Completed',
    badgeClass: 'bg-teal-500/10 text-teal-400 border-teal-500/20',
    dotClass: 'bg-teal-400',
  },
  Failed: {
    label: 'Failed',
    badgeClass: 'bg-rose-500/10 text-rose-400 border-rose-500/20',
    dotClass: 'bg-rose-400',
  },
  Archived: {
    label: 'Archived',
    badgeClass: 'bg-white/5 text-white/30 border-white/5',
    dotClass: 'bg-white/20',
  },
};
