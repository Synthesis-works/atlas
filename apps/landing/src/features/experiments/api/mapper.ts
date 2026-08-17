import type { 
  ProjectExecutionListEntryDto, 
  ExecutionReadDto, 
  ReportSummaryRead 
} from './experimentApi';
import type { 
  ExperimentRowModel, 
  ExperimentPreviewModel,
  ExperimentStatus,
  ExperimentTimelineEvent
} from '../types/catalog';

function mapStatus(backendStatus: string): ExperimentStatus {
  switch (backendStatus) {
    case 'QUEUED':
    case 'SCHEDULED':
      return 'Queued';
    case 'STARTING':
    case 'RUNNING':
    case 'EVALUATING':
    case 'RETRYING':
    case 'CANCELLING': // UI treats cancelling as active until it's cancelled
      return 'Running';
    case 'COMPLETED':
      return 'Completed';
    case 'FAILED':
      return 'Failed';
    case 'CANCELLED':
    case 'TIMED_OUT':
      return 'Cancelled';
    default:
      return 'Queued'; // Fallback
  }
}

function mapCurrentStage(backendStatus: string): string {
  switch (backendStatus) {
    case 'QUEUED': return 'Queued';
    case 'SCHEDULED': return 'Scheduled';
    case 'STARTING': return 'Starting';
    case 'RUNNING': return 'Running';
    case 'EVALUATING': return 'Evaluating';
    case 'RETRYING': return 'Retrying';
    case 'COMPLETED': return 'Completed';
    case 'FAILED': return 'Failed';
    case 'CANCELLED': return 'Cancelled';
    case 'TIMED_OUT': return 'Timed Out';
    default: return 'Unknown';
  }
}

function formatDuration(ms: number | null): string {
  if (ms == null) return '—';
  const totalSeconds = Math.floor(ms / 1000);
  if (totalSeconds < 60) return `${totalSeconds}s`;
  const m = Math.floor(totalSeconds / 60);
  const s = totalSeconds % 60;
  return `${m}m ${s}s`;
}

export function mapExecutionToRowModel(dto: ProjectExecutionListEntryDto): ExperimentRowModel {
  const status = mapStatus(dto.status);
  
  let progressPercentage: number | null = null;
  let stageCountText: string | null = null;
  if (dto.total_items > 0) {
    progressPercentage = Math.round((dto.completed_items / dto.total_items) * 100);
    stageCountText = `${dto.completed_items} / ${dto.total_items} items`;
  }

  // Tags can be derived from the target model and benchmark
  const tags = [dto.target_model];

  return {
    id: dto.id,
    name: dto.benchmark_name || 'Unknown Benchmark',
    status,
    progressPercentage,
    currentStage: mapCurrentStage(dto.status),
    stageCountText,
    etaText: null, // ETA not fabricated
    durationText: formatDuration(dto.duration),
    queuedAt: dto.created_at,
    tags
  };
}

export function mapExecutionToPreviewModel(
  execution: ExecutionReadDto, 
  report: ReportSummaryRead | null
): ExperimentPreviewModel {
  const status = mapStatus(execution.status);
  
  // Calculate duration from attempts or execution fields if available
  // If not natively available on ExecutionReadDto, we can approximate from attempts
  let durationMs = 0;
  let startedAt: string | null = null;
  
  const timeline: ExperimentTimelineEvent[] = execution.attempts.map((attempt) => {
    let attemptStatus: ExperimentTimelineEvent['status'] = 'pending';
    if (attempt.status === 'COMPLETED') attemptStatus = 'completed';
    else if (attempt.status === 'FAILED') attemptStatus = 'failed';
    else if (attempt.status === 'RUNNING') attemptStatus = 'active';

    let attemptDurationMs: number | undefined;
    if (attempt.started_at && attempt.finished_at) {
      attemptDurationMs = new Date(attempt.finished_at).getTime() - new Date(attempt.started_at).getTime();
      durationMs += attemptDurationMs;
    }
    
    if (!startedAt && attempt.started_at) {
      startedAt = attempt.started_at;
    }

    return {
      id: attempt.id,
      name: `Attempt ${attempt.attempt_number}`,
      status: attemptStatus,
      durationMs: attemptDurationMs
    };
  });

  const durationText = durationMs > 0 ? formatDuration(durationMs) : '—';
  
  const metrics: Record<string, any> = {};
  if (report) {
    if (report.overall_score != null) {
      metrics['Overall Score'] = report.overall_score;
    }
    report.scores.forEach(s => {
      metrics[s.capability_name] = s.score;
    });
  }

  return {
    id: execution.id,
    name: 'Execution', // We can enhance this if we have benchmark name in execution details
    status,
    owner: execution.created_by, // Map user ID or name if available
    startedAt,
    durationText,
    timeline,
    logs: null, // Fetched independently if a log artifact is present
    metrics,
    config: {
      target_model: report?.target_model || 'Unknown',
      benchmark_version: execution.benchmark_version_id,
      max_retries: execution.max_retries
    }
  };
}
