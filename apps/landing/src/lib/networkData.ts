/**
 * Atlas Intelligence Fabric — Network Data
 *
 * Nodes, edges, and category colors for the persistent canvas visualization.
 * The Fabric reads this data and renders it as a living constellation.
 */

export interface FabricNode {
  id: string;
  label: string;
  category: 'models' | 'benchmarks' | 'capabilities' | 'safety' | 'data' | 'output';
  radius: number;
  weight: number;
}

export interface FabricEdge {
  source: string;
  target: string;
}

export const FABRIC_NODES: FabricNode[] = [
  /* Core concepts — larger */
  { id: 'models',       label: 'Models',       category: 'models',       radius: 6,   weight: 1.0 },
  { id: 'benchmarks',   label: 'Benchmarks',   category: 'benchmarks',   radius: 6,   weight: 1.0 },
  { id: 'evaluations',  label: 'Evaluations',  category: 'output',       radius: 5.5, weight: 0.9 },
  { id: 'capabilities', label: 'Capabilities', category: 'capabilities', radius: 5.5, weight: 0.9 },
  { id: 'safety',       label: 'Safety',       category: 'safety',       radius: 5,   weight: 0.85 },
  { id: 'datasets',     label: 'Datasets',     category: 'data',         radius: 5,   weight: 0.85 },

  /* Models */
  { id: 'gpt4',    label: 'GPT-4',   category: 'models', radius: 3.5, weight: 0.6 },
  { id: 'claude',  label: 'Claude',  category: 'models', radius: 3.5, weight: 0.6 },
  { id: 'gemini',  label: 'Gemini',  category: 'models', radius: 3.5, weight: 0.6 },
  { id: 'llama',   label: 'LLaMA',   category: 'models', radius: 3,   weight: 0.55 },
  { id: 'mistral', label: 'Mistral', category: 'models', radius: 3,   weight: 0.55 },

  /* Benchmarks */
  { id: 'mmlu',      label: 'MMLU',      category: 'benchmarks', radius: 3.5, weight: 0.6 },
  { id: 'humaneval', label: 'HumanEval', category: 'benchmarks', radius: 3.5, weight: 0.6 },
  { id: 'gsm8k',     label: 'GSM8K',     category: 'benchmarks', radius: 3,   weight: 0.55 },
  { id: 'arc',       label: 'ARC',       category: 'benchmarks', radius: 3,   weight: 0.55 },
  { id: 'hellaswag', label: 'HellaSwag', category: 'benchmarks', radius: 2.5, weight: 0.5 },

  /* Capabilities */
  { id: 'reasoning',   label: 'Reasoning',   category: 'capabilities', radius: 3.5, weight: 0.6 },
  { id: 'coding',      label: 'Coding',      category: 'capabilities', radius: 3.5, weight: 0.6 },
  { id: 'mathematics', label: 'Mathematics', category: 'capabilities', radius: 3,   weight: 0.55 },
  { id: 'planning',    label: 'Planning',    category: 'capabilities', radius: 3,   weight: 0.55 },
  { id: 'language',    label: 'Language',    category: 'capabilities', radius: 2.5, weight: 0.5 },

  /* Safety */
  { id: 'toxicity',      label: 'Toxicity',      category: 'safety', radius: 3,   weight: 0.55 },
  { id: 'bias',          label: 'Bias',          category: 'safety', radius: 3,   weight: 0.55 },
  { id: 'hallucination', label: 'Hallucination', category: 'safety', radius: 3,   weight: 0.55 },

  /* Output */
  { id: 'reports',     label: 'Reports',     category: 'output', radius: 3.5, weight: 0.6 },
  { id: 'leaderboard', label: 'Leaderboard', category: 'output', radius: 3.5, weight: 0.6 },

  /* Data */
  { id: 'importers', label: 'Importers', category: 'data', radius: 2.5, weight: 0.5 },
  { id: 'metadata',  label: 'Metadata',  category: 'data', radius: 2.5, weight: 0.5 },
];

export const FABRIC_EDGES: FabricEdge[] = [
  /* Models ↔ Benchmarks */
  { source: 'models', target: 'benchmarks' },
  { source: 'models', target: 'evaluations' },
  { source: 'gpt4', target: 'mmlu' },
  { source: 'gpt4', target: 'humaneval' },
  { source: 'claude', target: 'mmlu' },
  { source: 'claude', target: 'arc' },
  { source: 'gemini', target: 'gsm8k' },
  { source: 'gemini', target: 'hellaswag' },
  { source: 'llama', target: 'humaneval' },
  { source: 'mistral', target: 'gsm8k' },

  /* Core connections */
  { source: 'models', target: 'capabilities' },
  { source: 'models', target: 'safety' },
  { source: 'benchmarks', target: 'capabilities' },
  { source: 'benchmarks', target: 'datasets' },
  { source: 'evaluations', target: 'reports' },
  { source: 'evaluations', target: 'leaderboard' },

  /* Models ↔ Core */
  { source: 'gpt4', target: 'models' },
  { source: 'claude', target: 'models' },
  { source: 'gemini', target: 'models' },
  { source: 'llama', target: 'models' },
  { source: 'mistral', target: 'models' },

  /* Benchmarks ↔ Core */
  { source: 'mmlu', target: 'benchmarks' },
  { source: 'humaneval', target: 'benchmarks' },
  { source: 'gsm8k', target: 'benchmarks' },
  { source: 'arc', target: 'benchmarks' },
  { source: 'hellaswag', target: 'benchmarks' },

  /* Capabilities */
  { source: 'reasoning', target: 'capabilities' },
  { source: 'coding', target: 'capabilities' },
  { source: 'mathematics', target: 'capabilities' },
  { source: 'planning', target: 'capabilities' },
  { source: 'language', target: 'capabilities' },
  { source: 'coding', target: 'humaneval' },
  { source: 'mathematics', target: 'gsm8k' },
  { source: 'reasoning', target: 'arc' },
  { source: 'reasoning', target: 'mmlu' },

  /* Safety */
  { source: 'toxicity', target: 'safety' },
  { source: 'bias', target: 'safety' },
  { source: 'hallucination', target: 'safety' },
  { source: 'safety', target: 'evaluations' },

  /* Data */
  { source: 'datasets', target: 'importers' },
  { source: 'datasets', target: 'metadata' },
  { source: 'datasets', target: 'evaluations' },

  /* Output */
  { source: 'reports', target: 'evaluations' },
  { source: 'leaderboard', target: 'evaluations' },
];

/** RGB values per category, used by the canvas renderer */
export const CATEGORY_COLORS: Record<string, [number, number, number]> = {
  models:       [129, 140, 248],
  benchmarks:   [103, 232, 249],
  capabilities: [167, 139, 250],
  safety:       [244, 114, 182],
  data:         [52, 211, 153],
  output:       [251, 191, 36],
};

/** Cluster positions (normalised 0–1) — where each category prefers to orbit */
export const CLUSTER_POSITIONS: Record<string, { cx: number; cy: number }> = {
  models:       { cx: 0.25, cy: 0.35 },
  benchmarks:   { cx: 0.65, cy: 0.25 },
  capabilities: { cx: 0.45, cy: 0.65 },
  safety:       { cx: 0.8,  cy: 0.6 },
  data:         { cx: 0.2,  cy: 0.72 },
  output:       { cx: 0.75, cy: 0.8 },
};
