import type { ModelStatus, DeploymentStatus, HealthStatus } from '@/domain/models/types';

const MODEL_STATUS: Record<ModelStatus, { label: string; dot: string; text: string }> = {
  active:       { label: 'Active',        dot: 'bg-green-500',   text: 'text-green-400' },
  beta:         { label: 'Beta',          dot: 'bg-yellow-400',  text: 'text-yellow-300' },
  experimental: { label: 'Experimental', dot: 'bg-orange-400',  text: 'text-orange-300' },
  deprecated:   { label: 'Deprecated',   dot: 'bg-white/30',    text: 'text-white/30' },
  archived:     { label: 'Archived',     dot: 'bg-white/20',    text: 'text-white/20' },
};

const DEPLOY_STATUS: Record<DeploymentStatus, { label: string; dot: string; text: string }> = {
  deployed:   { label: 'Deployed',   dot: 'bg-green-500', text: 'text-green-400' },
  deploying:  { label: 'Deploying',  dot: 'bg-yellow-400 animate-pulse', text: 'text-yellow-300' },
  stopped:    { label: 'Stopped',    dot: 'bg-white/20',  text: 'text-white/30' },
  error:      { label: 'Error',      dot: 'bg-red-500',   text: 'text-red-400' },
  none:       { label: 'None',       dot: 'bg-white/10',  text: 'text-white/20' },
};

const HEALTH_STATUS: Record<HealthStatus, { label: string; dot: string; text: string }> = {
  healthy:  { label: 'Healthy',  dot: 'bg-green-500', text: 'text-green-400' },
  degraded: { label: 'Degraded', dot: 'bg-yellow-400 animate-pulse', text: 'text-yellow-300' },
  down:     { label: 'Down',     dot: 'bg-red-500',   text: 'text-red-400' },
  unknown:  { label: 'Unknown',  dot: 'bg-white/20',  text: 'text-white/30' },
};

export function ModelStatusBadge({ status }: { status: ModelStatus }) {
  const s = MODEL_STATUS[status];
  return (
    <span className={`inline-flex items-center gap-1.5 text-xs ${s.text}`}>
      <span className={`w-1.5 h-1.5 rounded-full shrink-0 ${s.dot}`} />
      {s.label}
    </span>
  );
}

export function DeployStatusBadge({ status }: { status: DeploymentStatus }) {
  const s = DEPLOY_STATUS[status];
  return (
    <span className={`inline-flex items-center gap-1.5 text-xs ${s.text}`}>
      <span className={`w-1.5 h-1.5 rounded-full shrink-0 ${s.dot}`} />
      {s.label}
    </span>
  );
}

export function HealthStatusBadge({ status }: { status: HealthStatus }) {
  const s = HEALTH_STATUS[status];
  return (
    <span className={`inline-flex items-center gap-1.5 text-xs ${s.text}`}>
      <span className={`w-1.5 h-1.5 rounded-full shrink-0 ${s.dot}`} />
      {s.label}
    </span>
  );
}
