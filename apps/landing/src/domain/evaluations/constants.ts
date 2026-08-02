import type { EvaluationStatus, EvaluationPriority } from './types';

export const EVALUATION_STATUS_MAP: Record<
  EvaluationStatus,
  { label: string; badgeClass: string; dotClass: string }
> = {
  Queued: { label: 'Queued', badgeClass: 'bg-white/5 text-white/50 border-white/10', dotClass: 'bg-white/40' },
  Loading: { label: 'Loading', badgeClass: 'bg-blue-500/10 text-blue-400 border-blue-500/20', dotClass: 'bg-blue-400 animate-pulse' },
  Preparing: { label: 'Preparing', badgeClass: 'bg-indigo-500/10 text-indigo-400 border-indigo-500/20', dotClass: 'bg-indigo-400 animate-pulse' },
  Running: { label: 'Running', badgeClass: 'bg-emerald-500/10 text-emerald-400 border-emerald-500/20', dotClass: 'bg-emerald-400 animate-pulse' },
  Scoring: { label: 'Scoring', badgeClass: 'bg-cyan-500/10 text-cyan-400 border-cyan-500/20', dotClass: 'bg-cyan-400 animate-pulse' },
  Aggregating: { label: 'Aggregating', badgeClass: 'bg-teal-500/10 text-teal-400 border-teal-500/20', dotClass: 'bg-teal-400 animate-pulse' },
  Reporting: { label: 'Reporting', badgeClass: 'bg-purple-500/10 text-purple-400 border-purple-500/20', dotClass: 'bg-purple-400 animate-pulse' },
  Completed: { label: 'Completed', badgeClass: 'bg-teal-500/10 text-teal-400 border-teal-500/20', dotClass: 'bg-teal-400' },
  Failed: { label: 'Failed', badgeClass: 'bg-rose-500/10 text-rose-400 border-rose-500/20', dotClass: 'bg-rose-400' },
  Cancelled: { label: 'Cancelled', badgeClass: 'bg-orange-500/10 text-orange-400 border-orange-500/20', dotClass: 'bg-orange-400' },
  Paused: { label: 'Paused', badgeClass: 'bg-amber-500/10 text-amber-400 border-amber-500/20', dotClass: 'bg-amber-400' },
  Retrying: { label: 'Retrying', badgeClass: 'bg-sky-500/10 text-sky-400 border-sky-500/20', dotClass: 'bg-sky-400 animate-ping' },
};

export const EVALUATION_PRIORITY_MAP: Record<EvaluationPriority, { label: string; class: string; dot: string }> = {
  critical: { label: 'Critical', class: 'text-rose-400', dot: 'bg-rose-400' },
  high: { label: 'High', class: 'text-amber-400', dot: 'bg-amber-400' },
  normal: { label: 'Normal', class: 'text-white/50', dot: 'bg-white/30' },
  low: { label: 'Low', class: 'text-white/30', dot: 'bg-white/15' },
};

export const STAGE_PIPELINE = [
  { id: 'queued', name: 'Queued', icon: '◎' },
  { id: 'downloading', name: 'Downloading Dataset', icon: '⤓' },
  { id: 'preparing', name: 'Preparing Runtime', icon: '⚙' },
  { id: 'loading_model', name: 'Loading Model', icon: '◷' },
  { id: 'running', name: 'Running Tests', icon: '▶' },
  { id: 'scoring', name: 'Scoring', icon: '◈' },
  { id: 'aggregating', name: 'Aggregating', icon: '⊞' },
  { id: 'reporting', name: 'Generating Report', icon: '📄' },
  { id: 'completed', name: 'Completed', icon: '✓' },
] as const;

export const ACTIVE_STATUSES: EvaluationStatus[] = ['Running', 'Scoring', 'Aggregating', 'Reporting', 'Loading', 'Preparing'];

export const FAILURE_REASON_COLORS: Record<string, string> = {
  'Timeout': 'text-amber-400 bg-amber-500/10 border-amber-500/20',
  'GPU Error': 'text-rose-400 bg-rose-500/10 border-rose-500/20',
  'Dataset Error': 'text-orange-400 bg-orange-500/10 border-orange-500/20',
  'Model Crash': 'text-red-400 bg-red-500/10 border-red-500/20',
  'Network': 'text-blue-400 bg-blue-500/10 border-blue-500/20',
  'OOM': 'text-purple-400 bg-purple-500/10 border-purple-500/20',
  'Rate Limit': 'text-cyan-400 bg-cyan-500/10 border-cyan-500/20',
  'Config Error': 'text-yellow-400 bg-yellow-500/10 border-yellow-500/20',
};
