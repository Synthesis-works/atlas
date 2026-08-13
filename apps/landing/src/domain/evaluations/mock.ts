/**
 * Domain — Evaluations Mock Data v2
 * 250 evaluations · 5000 log lines · 40 reports · 12 models · 8 datasets · 15 benchmarks
 */

import type { EvaluationRun, EvaluationStageRecord, EvaluationReport, FailureReason } from './types';

// ── 12 Models ───────────────────────────────────────────────────────────────
const MODELS = [
  { name: 'GPT-5', provider: 'OpenAI' },
  { name: 'GPT-4o', provider: 'OpenAI' },
  { name: 'Claude-3.5-Sonnet', provider: 'Anthropic' },
  { name: 'Claude-3-Opus', provider: 'Anthropic' },
  { name: 'Gemini-2.0-Flash', provider: 'Google' },
  { name: 'Gemini-1.5-Pro', provider: 'Google' },
  { name: 'Llama-3.1-405B', provider: 'Meta' },
  { name: 'Llama-3-70B', provider: 'Meta' },
  { name: 'DeepSeek-V3', provider: 'DeepSeek' },
  { name: 'Qwen-2.5-72B', provider: 'Alibaba' },
  { name: 'Mistral-Large-2', provider: 'Mistral' },
  { name: 'Phi-4', provider: 'Microsoft' },
];

// ── 8 Datasets ──────────────────────────────────────────────────────────────
const DATASETS = [
  'MMLU-Pro Test v2',
  'HumanEval-Plus',
  'GSM8K Test Set',
  'TruthfulQA MC-v2',
  'SWE-bench Verified',
  'GPQA Diamond',
  'ARC-Challenge Test',
  'HellaSwag Validation',
];

// ── 15 Benchmarks ───────────────────────────────────────────────────────────
const BENCHMARKS = [
  { name: 'MMLU-Pro', category: 'reasoning' },
  { name: 'HumanEval', category: 'coding' },
  { name: 'GSM8K', category: 'mathematics' },
  { name: 'TruthfulQA', category: 'safety' },
  { name: 'SWE-bench', category: 'agents' },
  { name: 'ARC-Challenge', category: 'reasoning' },
  { name: 'HellaSwag', category: 'language' },
  { name: 'AGIEval', category: 'knowledge' },
  { name: 'GPQA', category: 'reasoning' },
  { name: 'Arena-Hard', category: 'reasoning' },
  { name: 'MBPP', category: 'coding' },
  { name: 'MT-Bench', category: 'language' },
  { name: 'BIG-Bench Hard', category: 'reasoning' },
  { name: 'DROP', category: 'mathematics' },
  { name: 'WinoGrande', category: 'language' },
];

const OWNERS = ['tushar', 'atlas-ci', 'research-team', 'eval-bot', 'dr-chen', 'ml-eng', 'nightly-runner'];
const WORKERS = ['worker-01', 'worker-02', 'worker-03', 'worker-04', 'worker-05', 'gpu-node-1', 'gpu-node-2', 'gpu-node-3', 'gpu-node-4'];
const TAGS_POOL = ['automated', 'ci', 'baseline', 'regression', 'comparison', 'research', 'prod', 'nightly', 'weekly', 'alpha', 'v2', 'ablation'];

// ── Status distribution: 50 Running, 30 Queued, 170 Completed + rest ────────
function buildStatusList(): EvaluationRun['status'][] {
  const list: EvaluationRun['status'][] = [];
  for (let i = 0; i < 50; i++) list.push('Running');
  for (let i = 0; i < 30; i++) list.push('Queued');
  for (let i = 0; i < 140; i++) list.push('Completed');
  for (let i = 0; i < 10; i++) list.push('Failed');
  for (let i = 0; i < 8; i++) list.push('Paused');
  for (let i = 0; i < 6; i++) list.push('Scoring');
  for (let i = 0; i < 3; i++) list.push('Aggregating');
  for (let i = 0; i < 2; i++) list.push('Retrying');
  for (let i = 0; i < 1; i++) list.push('Cancelled');
  return list;
}
const STATUS_LIST = buildStatusList();

const FAILURE_REASONS: FailureReason[] = ['Timeout', 'GPU Error', 'Dataset Error', 'Model Crash', 'Network', 'OOM', 'Rate Limit', 'Config Error'];

function makeDuration(minMin: number, maxMin: number) {
  return Math.floor(Math.random() * (maxMin - minMin + 1) + minMin) * 60 * 1000;
}

function makeTimestamp(minutesAgo: number) {
  return new Date(Date.now() - minutesAgo * 60 * 1000).toISOString();
}

function makeStages(status: EvaluationRun['status']): EvaluationStageRecord[] {
  const stages: EvaluationStageRecord[] = [
    { id: 's0', name: 'Queued', status: 'completed', durationMs: 5000 },
    { id: 's1', name: 'Downloading Dataset', status: 'completed', durationMs: 42000 },
    { id: 's2', name: 'Preparing Runtime', status: 'completed', durationMs: 18000 },
    { id: 's3', name: 'Loading Model', status: 'completed', durationMs: 88000 },
    { id: 's4', name: 'Running Tests', status: 'pending' },
    { id: 's5', name: 'Scoring', status: 'pending' },
    { id: 's6', name: 'Aggregating', status: 'pending' },
    { id: 's7', name: 'Generating Report', status: 'pending' },
  ];
  if (status === 'Loading') { stages[1].status = 'active'; stages[2].status = 'pending'; stages[3].status = 'pending'; }
  else if (status === 'Preparing') { stages[2].status = 'active'; stages[3].status = 'pending'; }
  else if (status === 'Running' || status === 'Retrying') { stages[4].status = 'active'; }
  else if (status === 'Scoring') { stages[4].status = 'completed'; stages[4].durationMs = 600000; stages[5].status = 'active'; }
  else if (status === 'Aggregating') { stages[4].status = 'completed'; stages[4].durationMs = 600000; stages[5].status = 'completed'; stages[5].durationMs = 90000; stages[6].status = 'active'; }
  else if (status === 'Reporting') { stages[4].status = 'completed'; stages[4].durationMs = 600000; stages[5].status = 'completed'; stages[5].durationMs = 90000; stages[6].status = 'completed'; stages[6].durationMs = 20000; stages[7].status = 'active'; }
  else if (status === 'Completed') { stages[4].status = 'completed'; stages[4].durationMs = 660000; stages[5].status = 'completed'; stages[5].durationMs = 95000; stages[6].status = 'completed'; stages[6].durationMs = 22000; stages[7].status = 'completed'; stages[7].durationMs = 18000; }
  else if (status === 'Failed') { stages[4].status = 'failed'; }
  else if (status === 'Queued') { stages[0].status = 'pending'; stages[1].status = 'pending'; stages[2].status = 'pending'; stages[3].status = 'pending'; }
  else if (status === 'Paused') { stages[4].status = 'active'; }
  return stages;
}

function makeEvalLog(model: string, benchmark: string, index: number): string[] {
  return [
    `[System] Atlas Evaluation Engine v2.4.0 initialized`,
    `[Queue] Job dequeued — priority: normal | worker: worker-0${(index % 9) + 1}`,
    `[Dataset] Fetching dataset from registry...`,
    `[Dataset] ${16000 + (index % 8000)} samples indexed in 2.1s`,
    `[Model] Connecting to ${model} inference endpoint...`,
    `[Model] Engine handshake completed (latency: ${18 + index % 40}ms)`,
    `[Runtime] Benchmark: ${benchmark} | batch_size: 32 | threads: 8`,
    `[Progress] Evaluated ${128 + index % 64}/1200 prompts (${(10 + index % 5).toFixed(1)}%) — Pass@1: ${(88 + index % 10).toFixed(1)}%`,
    `[Progress] Evaluated ${384 + index % 64}/1200 prompts — Pass@1: ${(90 + index % 8).toFixed(1)}%`,
    `[Scoring] Computing accuracy, precision, recall, F1...`,
    `[System] Evaluation completed in ${12 + index % 20}m ${index % 60}s`,
  ];
}

function seededRandom(seed: number) {
  let s = seed;
  return () => { s = (s * 1664525 + 1013904223) & 0xffffffff; return (s >>> 0) / 0xffffffff; };
}

export function makeEvaluation(index: number): EvaluationRun {
  const rng = seededRandom(index * 997 + 1);
  const status = STATUS_LIST[index % STATUS_LIST.length];
  const model = MODELS[index % MODELS.length];
  const benchmark = BENCHMARKS[index % BENCHMARKS.length];
  const dataset = DATASETS[index % DATASETS.length];
  const owner = OWNERS[index % OWNERS.length];
  const worker = WORKERS[index % WORKERS.length];
  const priority = (['critical', 'high', 'normal', 'normal', 'low'] as const)[index % 5];
  const progress = status === 'Completed' ? 100 : status === 'Queued' ? 0 : Math.floor(10 + (index * 13 + 7) % 88);
  const durationMs = makeDuration(4, 45);
  const minutesAgo = Math.floor(rng() * 480 + 1);
  const isCompleted = status === 'Completed';
  const isFailed = status === 'Failed';
  const score = 75 + (index % 24) + Math.floor(rng() * 3);
  const runNumber = index + 1;

  return {
    id: `eval-${String(runNumber).padStart(4, '0')}`,
    name: `${benchmark.name} × ${model.name} — Run #${runNumber}`,
    status,
    priority,
    model: model.name,
    modelProvider: model.provider,
    dataset,
    benchmark: benchmark.name,
    benchmarkCategory: benchmark.category,
    owner,
    progress,
    currentStage: status === 'Running' ? 'Running Tests' : status === 'Scoring' ? 'Scoring' : status === 'Aggregating' ? 'Aggregating' : status === 'Completed' ? 'Completed' : status === 'Queued' ? 'Queued' : status,
    worker,
    workerStatus: ['Running', 'Scoring', 'Aggregating', 'Reporting'].includes(status) ? 'busy' : 'idle',
    startedAt: makeTimestamp(minutesAgo),
    completedAt: isCompleted ? makeTimestamp(minutesAgo - Math.floor(durationMs / 60000)) : undefined,
    durationMs: isCompleted ? durationMs : undefined,
    estimatedDurationMs: durationMs,
    elapsedMs: isCompleted ? durationMs : Math.floor(progress / 100 * durationMs),
    queuedAt: makeTimestamp(minutesAgo + 8),
    metrics: isCompleted ? {
      accuracy: score / 100,
      precision: (score + 1.2) / 100,
      recall: (score - 1.8) / 100,
      f1: (score - 0.3) / 100,
      passAt1: (score + 2.1) / 100,
      latencyMs: 220 + Math.floor(rng() * 280),
      tokensPerSec: 45 + Math.floor(rng() * 80),
      hallucinationRate: 0.8 + rng() * 4.2,
      truthfulnessScore: (score + 3.1) / 100,
      toxicityScore: 0.002 + rng() * 0.04,
      costUsd: 0.02 + rng() * 0.18,
      gpuUtilPct: 62 + Math.floor(rng() * 33),
      memoryGb: 7 + Math.floor(rng() * 18),
      energyKwh: 0.08 + rng() * 0.42,
      overallScore: score / 100,
    } : undefined,
    stages: makeStages(status),
    logs: makeEvalLog(model.name, benchmark.name, index),
    artifacts: isCompleted ? [
      { id: `art-${index}-1`, filename: 'report.pdf', type: 'pdf', size: `${1 + (index % 6)} MB` },
      { id: `art-${index}-2`, filename: 'metrics.json', type: 'json', size: `${88 + (index % 400)} KB`, previewContent: `{\n  "accuracy": ${(score / 100).toFixed(3)},\n  "pass_at_1": ${((score + 2.1) / 100).toFixed(3)},\n  "latency_p50_ms": ${220 + Math.floor(rng() * 280)},\n  "cost_usd": ${(0.02 + rng() * 0.18).toFixed(2)},\n  "hallucination_rate": ${(0.8 + rng() * 4.2).toFixed(1)}\n}` },
      { id: `art-${index}-3`, filename: 'predictions.csv', type: 'csv', size: `${2 + (index % 12)} MB` },
      { id: `art-${index}-4`, filename: 'eval.log', type: 'log', size: `${180 + (index % 820)} KB` },
    ] : [],
    config: {
      temperature: 0,
      topP: 1,
      seed: 42 + index,
      maxTokens: 2048,
      batchSize: 32,
      threads: 8,
      timeout: `${20 + (index % 40)}m`,
      retries: 3,
      provider: model.provider.toLowerCase(),
      quantization: index % 4 === 0 ? 'int8' : index % 7 === 0 ? 'fp16' : undefined,
    },
    reproducibility: {
      modelVersion: `${model.name.toLowerCase().replace(/[^a-z0-9]/g, '-')}-v${1 + index % 3}.${index % 5}.0`,
      datasetVersion: `${index % 4 + 1}.0.${index % 3}`,
      benchmarkVersion: `${Math.floor(index / 15) + 1}.${index % 5}.0`,
      promptVersion: `v${1 + index % 5}`,
      commitSha: `sha256:${(index * 99999991).toString(16).padStart(16, '0')}`,
      dockerImage: `atlas-runner:${2 + index % 3}.${index % 8}.0`,
      runtime: `Atlas Engine v2.${3 + index % 2}`,
      seed: 42 + index,
      os: 'Ubuntu 22.04.3 LTS',
      pythonVersion: `3.${10 + index % 2}.${index % 8}`,
      cudaVersion: `12.${index % 4}`,
      engineVersion: `atlas-eval-v2.${3 + index % 2}.${index % 10}`,
    },
    tags: TAGS_POOL.filter((_, ti) => (index + ti) % 4 === 0).slice(0, 3),
    description: `Automated evaluation of ${model.name} on ${benchmark.name} (${benchmark.category}).`,
    error: isFailed ? MOCK_FAILURE_MESSAGES[index % MOCK_FAILURE_MESSAGES.length] : undefined,
    failureReason: isFailed ? FAILURE_REASONS[index % FAILURE_REASONS.length] : undefined,
    retryCount: status === 'Retrying' ? 1 + (index % 3) : 0,
  };
}

const MOCK_FAILURE_MESSAGES = [
  'Connection timeout to model endpoint after 3 retries',
  'CUDA out-of-memory on worker gpu-node-2: 24 GB exceeded',
  'Dataset shard download failed: HTTP 503 from registry',
  'Model process crashed (SIGABRT) — core dump saved',
  'Network partition: cannot reach inference API',
  'Rate limit exceeded: 429 Too Many Requests',
  'Invalid configuration: maxTokens > model context window',
];

// ── 250 Evaluations ─────────────────────────────────────────────────────────
export const MOCK_EVALUATIONS: EvaluationRun[] = Array.from({ length: 250 }, (_, i) => makeEvaluation(i));

export const ACTIVE_EVALUATIONS = MOCK_EVALUATIONS.filter(e =>
  ['Running', 'Scoring', 'Aggregating', 'Reporting', 'Loading', 'Preparing', 'Retrying'].includes(e.status)
);

// ── 40 Reports ──────────────────────────────────────────────────────────────
export const MOCK_REPORTS: EvaluationReport[] = Array.from({ length: 40 }, (_, i) => {
  const ev = MOCK_EVALUATIONS.filter(e => e.status === 'Completed')[i % 140];
  const types: EvaluationReport['type'][] = ['Full Report', 'Summary', 'Comparison', 'Debug Log'];
  const formats: EvaluationReport['format'][] = ['pdf', 'json', 'csv'];
  return {
    id: `report-${String(i + 1).padStart(3, '0')}`,
    evaluationId: ev?.id ?? `eval-${i + 1}`,
    evaluationName: ev?.name ?? `Evaluation #${i + 1}`,
    generatedAt: makeTimestamp(i * 18 + 10),
    size: `${0.5 + i * 0.3 < 10 ? (0.5 + i * 0.3).toFixed(1) : Math.floor(0.5 + i * 0.3)} MB`,
    type: types[i % types.length],
    format: formats[i % formats.length],
    model: ev?.model ?? MODELS[i % MODELS.length].name,
    benchmark: ev?.benchmark ?? BENCHMARKS[i % BENCHMARKS.length].name,
  };
});

// ── 5000 Runtime Log Lines ──────────────────────────────────────────────────


const LOG_TEMPLATES = [
  (i: number) => `[System] Atlas Evaluation Engine v2.4 heartbeat — ${i} jobs processed`,
  (i: number) => `[Queue] Dequeued eval-${String(i % 250 + 1).padStart(4, '0')} (priority: ${['critical','high','normal','low'][i%4]})`,
  (i: number) => `[Dataset] ${DATASETS[i % DATASETS.length]} — shard ${i % 8 + 1}/8 loaded (${(i % 4 + 1) * 4000} samples)`,
  (i: number) => `[Model] ${MODELS[i % MODELS.length].name} endpoint handshake: ${18 + i % 45}ms`,
  (i: number) => `[Executor] ${BENCHMARKS[i % BENCHMARKS.length].name} | batch ${i % 375 + 1}/375 | throughput: ${45 + i % 80} tok/s`,
  (i: number) => `[Progress] eval-${String(i % 250 + 1).padStart(4, '0')} — ${Math.min(100, Math.floor(i % 100 + 1))}% — Pass@1: ${(88 + i % 12).toFixed(1)}% — ETA: ${12 - Math.floor(i / 100)}m ${i % 60}s`,
  (i: number) => `[Scoring] eval-${String(i % 250 + 1).padStart(4, '0')} — accuracy: ${(0.75 + (i % 24) / 100).toFixed(3)} | hallucination: ${(0.01 + (i % 50) / 1000).toFixed(3)}`,
  (i: number) => `[Worker] ${WORKERS[i % WORKERS.length]} GPU util: ${62 + i % 34}% | VRAM: ${(16.2 + i % 8).toFixed(1)} GB / 24 GB`,
  (i: number) => `[Metrics] Tokens processed: ${(982000000 + i * 10000).toLocaleString()} | Cost: $${(0.04 + i * 0.001).toFixed(2)}`,
  (i: number) => `[Report] eval-${String(i % 250 + 1).padStart(4, '0')} — artifacts saved to /evaluations/run-${1000 + i}/`,
];

export const MOCK_RUNTIME_LOGS: string[] = Array.from({ length: 5000 }, (_, i) => {
  const now = new Date(Date.now() - (5000 - i) * 1200);
  const time = now.toLocaleTimeString('en-US', { hour12: false });
  return `${time} ${LOG_TEMPLATES[i % LOG_TEMPLATES.length](i)}`;
});

// ── Sparkline data for KPIs ─────────────────────────────────────────────────
export const MOCK_SPARK_RUNNING = Array.from({ length: 20 }, (_, i) => ({ t: i, v: 8 + Math.sin(i * 0.5) * 4 + (i === 19 ? 12 : 0) }));
export const MOCK_SPARK_SUCCESS = Array.from({ length: 20 }, (_, i) => ({ t: i, v: 92 + Math.sin(i * 0.3) * 3 }));
export const MOCK_SPARK_QUEUE = Array.from({ length: 20 }, (_, i) => ({ t: i, v: Math.max(5, 30 - i + Math.sin(i) * 5) }));
export const MOCK_SPARK_COST = Array.from({ length: 20 }, (_, i) => ({ t: i, v: 400 + i * 4 + Math.sin(i) * 20 }));

// ── Analytics chart data ─────────────────────────────────────────────────────
export const MOCK_RUNTIME_DISTRIBUTION = [
  { label: '0–5m', count: 18 },
  { label: '5–10m', count: 34 },
  { label: '10–20m', count: 62 },
  { label: '20–30m', count: 45 },
  { label: '30–45m', count: 28 },
  { label: '45m+', count: 13 },
];

export const MOCK_SUCCESS_RATE_TREND = Array.from({ length: 30 }, (_, i) => ({
  day: `Day ${i + 1}`,
  rate: 90 + Math.sin(i * 0.4) * 5 + (i > 20 ? 2 : 0),
}));

export const MOCK_QUEUE_LENGTH_TREND = Array.from({ length: 48 }, (_, i) => ({
  hour: `${String(Math.floor(i / 2)).padStart(2, '0')}:${i % 2 === 0 ? '00' : '30'}`,
  length: Math.max(0, 25 + Math.sin(i * 0.4) * 18 + (i > 30 ? -8 : 0)),
}));

export const MOCK_FAILURE_DISTRIBUTION = [
  { reason: 'Timeout', count: 28 },
  { reason: 'GPU Error', count: 19 },
  { reason: 'Dataset Error', count: 12 },
  { reason: 'Model Crash', count: 9 },
  { reason: 'Network', count: 7 },
  { reason: 'OOM', count: 5 },
  { reason: 'Rate Limit', count: 4 },
  { reason: 'Config Error', count: 2 },
];
