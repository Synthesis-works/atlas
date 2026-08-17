// Agent domain types — must exactly mirror the backend AgentTask/AgentStep response shapes.
// Source of truth: apps/backend/routers/agent.py  DO NOT add fictional model names.

export interface AgentPlanStep {
  step_number: number;
  description: string;
  status: 'PENDING' | 'IN_PROGRESS' | 'COMPLETED' | 'FAILED' | 'REPAIRED' | 'RUNNING'; // added IN_PROGRESS, REPAIRED
  result_summary?: string | null;
}

export interface AgentToolCall {
  call_id: string;
  tool_name: string;
  arguments: Record<string, any>;
  timestamp: string;
}

export interface AgentObservation {
  call_id: string;
  tool_name: string;
  success: boolean;
  output: any;
  error?: string | null;
  timestamp: string;
}

export interface AgentExecutionTrace {
  event_type: string;
  timestamp: string;
  details: Record<string, any>;
}

// Status values as returned by the backend AgentTaskStatus enum
export type AgentTaskStatus =
  | 'PENDING'
  | 'PLANNING'
  | 'EXECUTING'
  | 'REPAIRING'
  | 'WAITING_FOR_CLARIFICATION'
  | 'WAITING_FOR_APPROVAL'
  | 'COMPLETED'
  | 'FAILED'
  | 'CANCELLED';

export interface AgentTask {
  // Backend returns task_id (UUID) as the primary key — not "id"
  task_id: string;
  goal: string;
  status: AgentTaskStatus;
  step_count: number;
  total_tool_calls: number;
  repair_attempts?: number;
  primary_provider?: string;
  current_provider?: string;
  plan: AgentPlanStep[];
  tool_calls?: AgentToolCall[];
  observations?: AgentObservation[];
  execution_trace?: AgentExecutionTrace[];
  final_result?: Record<string, any> | string | null;
  error_detail?: string | null;
  report_id?: string | null;
  // Clarification fields
  clarification_request?: string | null;
  clarification_prompt?: string | null;
  clarification_id?: string | null;
  clarification_attempts?: number;
  clarification_answer?: string | null;
  clarification_requested_at?: string | null;
  past_clarifications?: Array<{ question: string; answer: string; fingerprint: string; answered_at: string }>;
  // Approval fields
  pending_tool_call?: any | null;
  approval_token?: string | null;
  // Run metadata
  run_mode?: string;
  source_task_id?: string | null;
  benchmark_id?: string | null;
  benchmark_version_id?: string | null;
  dataset_id?: string | null;
  dataset_version_id?: string | null;
  execution_ids?: string[];
  // Timestamps
  created_at?: string | null;
  started_at?: string | null;
  completed_at?: string | null;
}

// Real report metadata returned by GET /api/v1/agent/reports/{report_id}
export interface AgentReportMetric {
  metric_name: string;
  metric_value: number;
}

export interface AgentReport {
  report_id: string;
  benchmark_id: string | null;
  title: string;
  summary: string | null;
  version_string: string;
  execution_id: string | null;
  published: boolean;
  created_at: string;
  metrics: AgentReportMetric[];
}

// Dynamic Agent Provider Option from Backend
export interface AgentProviderOption {
  value: string;
  label: string;
  description: string;
  model: string;
  is_test_only?: boolean;
}


