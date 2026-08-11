/**
 * Domain — Research
 * The Atlas Evaluation Methodology, Capability Taxonomy,
 * Benchmark Evolution roadmap, and future research directions.
 */

/* ----------------------------------------------------------------------- */

export interface AEMStage {
  id: string;
  name: string;
  description: string;
  order: number;
}

export interface CapabilityTaxonomyLevel {
  domain: string;
  capabilities: string[];
  description: string;
  details: string;
  benchmarks: string[];
}

export interface BenchmarkEvolutionPhase {
  version: string;
  name: string;
  focus: string;
  description: string;
}

export interface FutureDirection {
  id: string;
  title: string;
  description: string;
  status: 'research' | 'planned' | 'future';
  details: string;
  milestones: string[];
}

/* ----------------------------------------------------------------------- */

export const AEM_STAGES: AEMStage[] = [
  {
    id: 'observation',
    name: 'Observation',
    description: 'Execute benchmarks against models. Capture raw outputs immutably.',
    order: 1,
  },
  {
    id: 'measurement',
    name: 'Measurement',
    description: 'Apply judge strategies — hidden tests, exact match, rule engines — to score outputs.',
    order: 2,
  },
  {
    id: 'interpretation',
    name: 'Interpretation',
    description: 'Map scores to capability dimensions. Aggregate into multi-dimensional profiles.',
    order: 3,
  },
  {
    id: 'reporting',
    name: 'Reporting',
    description: 'Generate verified reports. Build capability genomes. Populate leaderboards.',
    order: 4,
  },
];

export const CAPABILITY_TAXONOMY: CapabilityTaxonomyLevel[] = [
  {
    domain: 'Coding',
    capabilities: ['Generation', 'Debugging', 'Refactoring', 'Testing'],
    description: 'Code synthesis, comprehension, and transformation abilities.',
    details: 'Evaluates correctness, syntax adherence, refactoring quality, and test suite generation in sandboxed runtimes.',
    benchmarks: ['HumanEval (Python)', 'MBPP (Basic Tasks)', 'SWE-bench (Software Engineering)', 'MultiPL-E (Cross-lingual)'],
  },
  {
    domain: 'Reasoning',
    capabilities: ['Logical', 'Spatial', 'Temporal', 'Causal'],
    description: 'Structured thinking and multi-step inference.',
    details: 'Measures multi-step logical deductions, spatial relation mapping, temporal timelines, and causal relationship tracking.',
    benchmarks: ['ARC-Challenge', 'HellaSwag', 'LogiQA', 'BIG-bench Hard'],
  },
  {
    domain: 'Mathematics',
    capabilities: ['Arithmetic', 'Algebra', 'Calculus', 'Statistics'],
    description: 'Numerical computation and mathematical problem solving.',
    details: 'Assesses symbolic algebra, multi-step calculation correctness, statistics, and advanced calculus reasoning.',
    benchmarks: ['GSM8K (Grade School)', 'MATH Dataset', 'MMLU Mathematics', 'SVAMP'],
  },
  {
    domain: 'Planning',
    capabilities: ['Task Planning', 'Multi-step', 'Resource Allocation', 'Scheduling'],
    description: 'Decomposing goals into executable sequences.',
    details: 'Tests long-horizon task scheduling, pathfinding, dynamic resource allocation, and target decomposition.',
    benchmarks: ['Blocksworld (LLM)', 'TravelPlanner', 'WebArena Tasking', 'GAIA planning'],
  },
  {
    domain: 'Tool Use',
    capabilities: ['API Calling', 'Function Composition', 'Environment Interaction', 'Code Execution'],
    description: 'Using external tools, APIs, and environments effectively.',
    details: 'Validates API parameter matching, multi-function calling, tool output parsing, and dynamic environment reactions.',
    benchmarks: ['ToolBench', 'Gorilla API', 'Berkeley Function Calling', 'AgentBench'],
  },
  {
    domain: 'Safety',
    capabilities: ['Toxicity', 'Bias', 'Hallucination', 'Jailbreak Resistance'],
    description: 'Alignment with safety standards and harmlessness.',
    details: 'Measures resistance to adversarial prompts, demographic bias, toxic output triggers, and hallucination rates.',
    benchmarks: ['RealToxicityPrompts', 'TruthfulQA', 'Do-Not-Answer', 'AdversarialGLUE'],
  },
  {
    domain: 'Knowledge',
    capabilities: ['Factual', 'Temporal', 'Domain Expertise', 'Multilingual'],
    description: 'Breadth and accuracy of stored knowledge.',
    details: 'Verifies global trivia factual correctness, multilingual accuracy, temporal context decay, and specialized domain recall.',
    benchmarks: ['MMLU (Global Knowledge)', 'TriviaQA', 'GPQA (Graduate Level)', 'WikiQA'],
  },
  {
    domain: 'Language',
    capabilities: ['Fluency', 'Coherence', 'Summarization', 'Translation'],
    description: 'Natural language understanding and generation quality.',
    details: 'Scores grammar fluency, context coherence, summarization fidelity, and translation accuracy.',
    benchmarks: ['WMT Translation', 'CNN/DailyMail Summary', 'Rogue/BLEU scoreboards', 'CoLA (Linguistics)'],
  },
];

export const ATLAS_EVOLUTION: BenchmarkEvolutionPhase[] = [
  { version: '1.0', name: 'Core Platform', focus: 'Foundation', description: 'Benchmark management, execution, evaluation, reporting, dashboard.' },
  { version: '2.0', name: 'Community Benchmarks', focus: 'Ecosystem', description: 'Publishing, reputation, reviews, public leaderboards.' },
  { version: '3.0', name: 'Intelligent Evaluation', focus: 'Intelligence', description: 'Adaptive benchmarks, LLM-assisted evaluation, confidence estimation.' },
  { version: '4.0', name: 'Enterprise Platform', focus: 'Scale', description: 'Organizations, teams, RBAC expansion, compliance, audit.' },
  { version: '5.0', name: 'Global Infrastructure', focus: 'Universal', description: 'Distributed execution, federated registry, marketplace, plugins.' },
];

export const FUTURE_RESEARCH: FutureDirection[] = [
  {
    id: 'llm-judge',
    title: 'LLM-as-Judge',
    description: 'Using language models to evaluate other models on subjective and open-ended tasks where rule-based judges fall short.',
    status: 'planned',
    details: 'Developing robust meta-evaluators aligned with human consensus on complex reasoning, coding, and safety tasks.',
    milestones: ['Bias Mitigation Studies', 'Calibration Classifiers', 'Consistency Checklists'],
  },
  {
    id: 'adaptive-benchmarks',
    title: 'Adaptive Benchmarks',
    description: 'Benchmarks that evolve based on a model\'s demonstrated weaknesses, preventing saturation and training-data contamination.',
    status: 'research',
    details: 'Building dynamic question sets that adjust test difficulty on the fly based on historical model responses.',
    milestones: ['Dynamic Generators', 'Contamination Detectors', 'Adversarial Prompting Engines'],
  },
  {
    id: 'contamination-analysis',
    title: 'Contamination Analysis',
    description: 'Detecting when benchmark content has leaked into training data, ensuring evaluation results remain valid.',
    status: 'research',
    details: 'Detecting training set leaks using token frequency, n-gram extraction, and model memory checking.',
    milestones: ['N-Gram Extraction Runs', 'Pre-training Verification', 'Fingerprinting Models'],
  },
  {
    id: 'consensus-judges',
    title: 'Consensus & Committee Judges',
    description: 'Multiple evaluation strategies voting on outcomes — combining LLM judges, rule engines, and human review.',
    status: 'future',
    details: 'Combining structured code tests, rule matches, and LLM votes to yield a unified evaluation consensus.',
    milestones: ['Multi-agent voting rules', 'Deterministic code execution', 'Human-in-the-loop audit logs'],
  },
  {
    id: 'capability-genome',
    title: 'Capability Genome Evolution',
    description: 'Tracking how a model\'s capability vector changes over time, across versions, and under different conditions.',
    status: 'research',
    details: 'Tracking versioned model histories in the registry to plot score evolution and regression graphs.',
    milestones: ['Capability Vector Mapping', 'Regression Tracking Alerts', 'Semantic Shift Analyzers'],
  },
  {
    id: 'cross-model-transfer',
    title: 'Cross-Model Transfer Analysis',
    description: 'Understanding how capabilities demonstrated on one benchmark transfer to unseen tasks and domains.',
    status: 'future',
    details: 'Studying how model competence on synthetic benchmarks correlates with performance on real-world workflow tasks.',
    milestones: ['Transfer Correlation Models', 'Synthetic vs. Real Tasks', 'Generalization Metrics'],
  },
];
