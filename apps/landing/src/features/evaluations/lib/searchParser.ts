/**
 * Evaluations Search Parser
 * Extends the Benchmarks searchParser pattern with comparator support.
 *
 * Supported tokens:
 *   status:running         exact match (case-insensitive)
 *   model:llama3           substring match on model name
 *   dataset:mmlu           substring match on dataset
 *   benchmark:reasoning    substring match on benchmark or category
 *   owner:tushar           substring match on owner
 *   runtime>20m            numeric comparator (>,<,>=,<=) on durationMs
 *   score>85               numeric comparator on overallScore × 100
 *   priority:high          exact match on priority
 *   worker:gpu-node-1      substring match on worker
 *   tag:baseline           substring match on tags
 *   provider:openai        substring match on modelProvider
 */

import type { EvaluationRun } from '@/domain/evaluations/types';

export interface EvalFilterCriteria {
  textQuery: string;
  status?: string;
  model?: string;
  dataset?: string;
  benchmark?: string;
  owner?: string;
  priority?: string;
  worker?: string;
  tag?: string;
  provider?: string;
  runtimeOp?: '>' | '<' | '>=' | '<=';
  runtimeMs?: number;
  scoreOp?: '>' | '<' | '>=' | '<=';
  scoreVal?: number;
}

function parseComparator(token: string): { op: '>' | '<' | '>=' | '<='; value: number; key: string } | null {
  const match = token.match(/^([a-z]+)(>=|<=|>|<)(.+)$/i);
  if (!match) return null;
  const [, key, op, raw] = match;
  // Convert time strings like 20m, 5s to ms
  let value: number;
  if (/^\d+m$/i.test(raw)) value = parseInt(raw) * 60000;
  else if (/^\d+s$/i.test(raw)) value = parseInt(raw) * 1000;
  else value = parseFloat(raw);
  return { key: key.toLowerCase(), op: op as any, value };
}

function applyComparator(actual: number, op: string, threshold: number): boolean {
  if (op === '>') return actual > threshold;
  if (op === '<') return actual < threshold;
  if (op === '>=') return actual >= threshold;
  if (op === '<=') return actual <= threshold;
  return true;
}

export function parseEvalSearchQuery(query: string): EvalFilterCriteria {
  const criteria: EvalFilterCriteria = { textQuery: '' };
  const tokens = query.trim().split(/\s+/);
  const textParts: string[] = [];

  tokens.forEach(token => {
    if (!token) return;

    // Try comparator first: runtime>20m, score>85
    const comp = parseComparator(token);
    if (comp) {
      if (comp.key === 'runtime') { criteria.runtimeOp = comp.op; criteria.runtimeMs = comp.value; return; }
      if (comp.key === 'score') { criteria.scoreOp = comp.op; criteria.scoreVal = comp.value; return; }
    }

    // Key:value pairs
    if (token.includes(':')) {
      const colonIdx = token.indexOf(':');
      const key = token.slice(0, colonIdx).toLowerCase();
      const val = token.slice(colonIdx + 1).toLowerCase();
      if (key === 'status') { criteria.status = val; return; }
      if (key === 'model') { criteria.model = val; return; }
      if (key === 'dataset') { criteria.dataset = val; return; }
      if (key === 'benchmark' || key === 'bm') { criteria.benchmark = val; return; }
      if (key === 'owner') { criteria.owner = val; return; }
      if (key === 'priority') { criteria.priority = val; return; }
      if (key === 'worker') { criteria.worker = val; return; }
      if (key === 'tag' || key === 'tags') { criteria.tag = val; return; }
      if (key === 'provider') { criteria.provider = val; return; }
    }

    textParts.push(token.toLowerCase());
  });

  criteria.textQuery = textParts.join(' ');
  return criteria;
}

export function filterEvaluations(evaluations: EvaluationRun[], query: string): EvaluationRun[] {
  if (!query.trim()) return evaluations;

  const c = parseEvalSearchQuery(query);

  return evaluations.filter(ev => {
    if (c.status && ev.status.toLowerCase() !== c.status) return false;
    if (c.model && !ev.model.toLowerCase().includes(c.model)) return false;
    if (c.dataset && !ev.dataset.toLowerCase().includes(c.dataset)) return false;
    if (c.benchmark && !ev.benchmark.toLowerCase().includes(c.benchmark) && !ev.benchmarkCategory.toLowerCase().includes(c.benchmark)) return false;
    if (c.owner && !ev.owner.toLowerCase().includes(c.owner)) return false;
    if (c.priority && ev.priority !== c.priority) return false;
    if (c.worker && !ev.worker.toLowerCase().includes(c.worker)) return false;
    if (c.tag && !ev.tags.some(t => t.toLowerCase().includes(c.tag!))) return false;
    if (c.provider && !ev.modelProvider.toLowerCase().includes(c.provider)) return false;

    if (c.runtimeMs !== undefined && c.runtimeOp) {
      const actual = ev.durationMs ?? ev.elapsedMs ?? 0;
      if (!applyComparator(actual, c.runtimeOp, c.runtimeMs)) return false;
    }

    if (c.scoreVal !== undefined && c.scoreOp) {
      const actual = (ev.metrics?.overallScore ?? 0) * 100;
      if (!applyComparator(actual, c.scoreOp, c.scoreVal)) return false;
    }

    if (c.textQuery) {
      const q = c.textQuery;
      const hit = ev.name.toLowerCase().includes(q) ||
        ev.model.toLowerCase().includes(q) ||
        ev.benchmark.toLowerCase().includes(q) ||
        ev.dataset.toLowerCase().includes(q) ||
        ev.owner.toLowerCase().includes(q) ||
        ev.id.toLowerCase().includes(q);
      if (!hit) return false;
    }

    return true;
  });
}
