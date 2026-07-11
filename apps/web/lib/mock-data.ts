export const MOCK_PROJECTS = [
  { id: "proj-1", name: "Core Models Evaluation", description: "Evaluating foundation models across coding and reasoning domains.", runs: 142, team: 4, status: "Active", lastActive: "2 hours ago" },
  { id: "proj-2", name: "Safety Alignment Checks", description: "Adversarial testing against Llama 3 70B to ensure compliance.", runs: 38, team: 2, status: "Active", lastActive: "1 day ago" },
  { id: "proj-3", name: "RAG Pipeline v2", description: "Retrieval augmented generation latency and accuracy tests.", runs: 12, team: 5, status: "Paused", lastActive: "1 week ago" },
];

export const MOCK_BENCHMARKS = [
  { id: "human-eval", name: "HumanEval v1.2", category: "Coding", desc: "Python coding tasks evaluating functional correctness.", difficulty: "Medium", datasets: 1 },
  { id: "mmlu", name: "MMLU", category: "Knowledge", desc: "Massive Multitask Language Understanding across 57 subjects.", difficulty: "Hard", datasets: 4 },
  { id: "swe-bench", name: "SWE-bench", category: "Coding", desc: "Resolving real-world GitHub issues in Python repositories.", difficulty: "Expert", datasets: 1 },
  { id: "gsm8k", name: "GSM8K", category: "Mathematics", desc: "Grade school math word problems requiring multi-step reasoning.", difficulty: "Medium", datasets: 1 },
  { id: "arc", name: "AI2 Reasoning Challenge", category: "Reasoning", desc: "Grade-school science questions requiring logic and knowledge.", difficulty: "Medium", datasets: 2 },
  { id: "advbench", name: "AdvBench", category: "Safety", desc: "Adversarial prompts testing alignment and safety guardrails.", difficulty: "Hard", datasets: 1 },
];

export const MOCK_EXECUTIONS = [
  { id: "ATL-RUN-0921", model: "gpt-4o", benchmark: "HumanEval", version: "v1.2", status: "Running", start: "2 mins ago", duration: "-", user: "JD" },
  { id: "ATL-RUN-0920", model: "claude-3.5-sonnet", benchmark: "SWE-bench", version: "v1.0", status: "Completed", start: "1 hour ago", duration: "45m 12s", user: "JD" },
  { id: "ATL-RUN-0919", model: "llama-3-70b", benchmark: "MMLU", version: "v2.1", status: "Failed", start: "3 hours ago", duration: "1m 02s", user: "TS" },
  { id: "ATL-RUN-0918", model: "gpt-4o", benchmark: "RepoBench", version: "v1.0", status: "Completed", start: "5 hours ago", duration: "12m 40s", user: "JD" },
  { id: "ATL-RUN-0917", model: "gemini-1.5-pro", benchmark: "GSM8K", version: "v1.0", status: "Completed", start: "Yesterday", duration: "8m 15s", user: "MK" },
  { id: "ATL-RUN-0916", model: "claude-3-opus", benchmark: "AdvBench", version: "v1.1", status: "Cancelled", start: "Yesterday", duration: "0m 12s", user: "JD" },
];

export const MOCK_REPORTS = [
  { id: "REP-01", name: "GPT-4o Capability Profile", type: "Detailed Analysis", benchmark: "Multiple", date: "Oct 24, 2026", size: "2.4 MB" },
  { id: "REP-02", name: "Claude 3.5 Sonnet vs GPT-4o", type: "Comparison", benchmark: "HumanEval & SWE-bench", date: "Oct 22, 2026", size: "1.8 MB" },
  { id: "REP-03", name: "Llama 3 70B Safety Audit", type: "Compliance", benchmark: "AdvBench", date: "Oct 15, 2026", size: "3.1 MB" },
  { id: "REP-04", name: "Q3 Core Models Summary", type: "Executive Summary", benchmark: "Multiple", date: "Oct 01, 2026", size: "4.5 MB" },
];

export const MOCK_RANKINGS: Record<string, any[]> = {
  "Coding": [
    { rank: 1, model: "gpt-4o", score: 92.4, change: "+1.2", badge: "State of the Art" },
    { rank: 2, model: "claude-3.5-sonnet", score: 91.8, change: "+2.4", badge: "Top Tier" },
    { rank: 3, model: "llama-3-70b-instruct", score: 86.5, change: "0.0", badge: "Open Weights" },
    { rank: 4, model: "gemini-1.5-pro", score: 85.2, change: "-0.5" },
    { rank: 5, model: "mixtral-8x22b", score: 81.4, change: "+0.8" },
  ],
  "Reasoning": [
    { rank: 1, model: "claude-3.5-sonnet", score: 94.1, change: "+3.1", badge: "State of the Art" },
    { rank: 2, model: "gpt-4o", score: 92.8, change: "+0.5", badge: "Top Tier" },
    { rank: 3, model: "gemini-1.5-pro", score: 89.4, change: "+1.1" },
    { rank: 4, model: "llama-3-70b-instruct", score: 88.0, change: "0.0", badge: "Open Weights" },
  ],
  "Mathematics": [
    { rank: 1, model: "gpt-4o", score: 89.2, change: "+2.0", badge: "State of the Art" },
    { rank: 2, model: "claude-3.5-sonnet", score: 88.1, change: "+1.1", badge: "Top Tier" },
  ],
  "Tool Use": [
    { rank: 1, model: "gpt-4o", score: 95.1, change: "+0.2", badge: "State of the Art" },
  ],
  "Safety": [
    { rank: 1, model: "claude-3-opus", score: 98.4, change: "0.0", badge: "Safest" },
    { rank: 2, model: "llama-3-70b-instruct", score: 96.2, change: "+1.0" },
  ]
};

export const MOCK_CHART_DATA = [
  { name: 'Mon', coding: 84, reasoning: 72 },
  { name: 'Tue', coding: 85, reasoning: 74 },
  { name: 'Wed', coding: 87, reasoning: 75 },
  { name: 'Thu', coding: 89, reasoning: 79 },
  { name: 'Fri', coding: 92, reasoning: 84 },
  { name: 'Sat', coding: 91, reasoning: 85 },
  { name: 'Sun', coding: 94, reasoning: 88 },
];
