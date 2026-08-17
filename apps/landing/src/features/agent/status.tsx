import type { ReactNode } from 'react';
import {
  AlertTriangle,
  CheckCircle2,
  Clock,
  HelpCircle,
  Loader2,
  Square,
  XCircle,
} from 'lucide-react';
import type { AgentTaskStatus } from './types';

/**
 * Semantic status system for the Atlas Agent.
 *
 * Lifecycle colors (the user-facing visual language):
 *   success   -> GREEN  : finished / completed
 *   working   -> BLUE   : executing / planning (subtle pulse while active)
 *   attention -> YELLOW : clarification / needs input
 *   danger    -> RED    : failed / stopped / cancelled
 *   neutral   -> GRAY   : pending / not started
 *
 * Atlas purple remains the brand/action color and is never used for a lifecycle status.
 */

export type StatusTone = 'success' | 'working' | 'attention' | 'danger' | 'neutral';

export interface StatusToneClasses {
  text: string;
  bg: string;
  border: string;
  dot: string;
}

export const STATUS_TONES: Record<StatusTone, StatusToneClasses> = {
  success: {
    text: 'text-emerald-300',
    bg: 'bg-emerald-500/10',
    border: 'border-emerald-500/30',
    dot: 'bg-emerald-400',
  },
  working: {
    text: 'text-sky-300',
    bg: 'bg-sky-500/10',
    border: 'border-sky-500/30',
    dot: 'bg-sky-400',
  },
  attention: {
    text: 'text-amber-300',
    bg: 'bg-amber-500/10',
    border: 'border-amber-500/30',
    dot: 'bg-amber-400',
  },
  danger: {
    text: 'text-red-300',
    bg: 'bg-red-500/10',
    border: 'border-red-500/30',
    dot: 'bg-red-400',
  },
  neutral: {
    text: 'text-white/45',
    bg: 'bg-white/[0.04]',
    border: 'border-white/10',
    dot: 'bg-white/25',
  },
};

const TASK_TONE: Record<AgentTaskStatus, StatusTone> = {
  COMPLETED: 'success',
  PENDING: 'working',
  PLANNING: 'working',
  EXECUTING: 'working',
  REPAIRING: 'working',
  WAITING_FOR_CLARIFICATION: 'attention',
  WAITING_FOR_APPROVAL: 'attention',
  FAILED: 'danger',
  CANCELLED: 'danger',
};

export function taskTone(status: AgentTaskStatus): StatusTone {
  return TASK_TONE[status] ?? 'neutral';
}

export function taskStatusLabel(status: AgentTaskStatus): string {
  switch (status) {
    case 'COMPLETED':
      return 'Completed';
    case 'PENDING':
      return 'Queued';
    case 'PLANNING':
      return 'Planning';
    case 'EXECUTING':
      return 'Running';
    case 'REPAIRING':
      return 'Repairing';
    case 'WAITING_FOR_CLARIFICATION':
      return 'Needs input';
    case 'WAITING_FOR_APPROVAL':
      return 'Needs approval';
    case 'FAILED':
      return 'Failed';
    case 'CANCELLED':
      return 'Stopped';
    default:
      return 'Unknown';
  }
}

export function taskStatusIcon(status: AgentTaskStatus, className = 'w-3.5 h-3.5') {
  switch (status) {
    case 'COMPLETED':
      return <CheckCircle2 className={className} />;
    case 'PENDING':
      return <Clock className={className} />;
    case 'PLANNING':
    case 'EXECUTING':
    case 'REPAIRING':
      return <Loader2 className={className} />;
    case 'WAITING_FOR_CLARIFICATION':
      return <HelpCircle className={className} />;
    case 'WAITING_FOR_APPROVAL':
      return <AlertTriangle className={className} />;
    case 'FAILED':
      return <XCircle className={className} />;
    case 'CANCELLED':
      return <Square className={className} />;
    default:
      return null;
  }
}

export function StatusDot({ tone, pulse = false }: { tone: StatusTone; pulse?: boolean }) {
  const cls = STATUS_TONES[tone].dot;
  return (
    <span className="relative inline-flex w-2 h-2">
      <span className={`absolute inline-flex w-2 h-2 rounded-full ${cls} ${pulse ? 'animate-ping opacity-60' : ''}`} />
      <span className={`relative inline-flex w-2 h-2 rounded-full ${cls}`} />
    </span>
  );
}

export function StatusBadge({
  tone,
  label,
  icon,
  className = '',
}: {
  tone: StatusTone;
  label: string;
  icon?: ReactNode;
  className?: string;
}) {
  const c = STATUS_TONES[tone];
  return (
    <span
      className={`inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-md text-[11px] font-semibold border ${c.bg} ${c.border} ${c.text} ${className}`}
    >
      {icon ?? <StatusDot tone={tone} />}
      {label}
    </span>
  );
}

export function AgentStatusBadge({
  status,
  className = '',
}: {
  status: AgentTaskStatus;
  className?: string;
}) {
  const tone = taskTone(status);
  return (
    <StatusBadge
      tone={tone}
      label={taskStatusLabel(status)}
      icon={taskStatusIcon(status)}
      className={className}
    />
  );
}
